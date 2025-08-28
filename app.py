import os
import uuid
# MODIFIED LINE BELOW   
from datetime import datetime, timedelta 
from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models

class Faculty(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(10), unique=True, nullable=False) 
    department = db.Column(db.String(100), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    scan_records = db.relationship('ScanRecord', backref='faculty', lazy=True)

class ScanRecord(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    faculty_id = db.Column(db.String(36), db.ForeignKey('faculty.id'), nullable=False)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)


latest_scan = None

# Routes
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        department = request.form.get('department')
        
        # Check if faculty already exists
        existing_faculty = Faculty.query.filter_by(phone_number=phone_number).first()
        if existing_faculty:
            # Faculty already registered, store their ID in cookie and redirect
            response = make_response(redirect(url_for('scan_success')))
            response.set_cookie('faculty_id', existing_faculty.id, max_age=60*60*24*365)  # 1 year
            return response
        
        # Create new faculty
        faculty = Faculty(name=name, phone_number=phone_number, department=department)
        db.session.add(faculty)
        db.session.commit()
        
        # Store faculty ID in cookie
        response = make_response(redirect(url_for('scan_success')))
        response.set_cookie('faculty_id', faculty.id, max_age=60*60*24*365)  # 1 year
        return response
    
    return render_template('register.html')

@app.route('/scan')
def scan():
    global latest_scan
    
    faculty_id = request.cookies.get('faculty_id')
    
    if not faculty_id:
        return redirect(url_for('register'))
    
    faculty = Faculty.query.get(faculty_id)
    if not faculty:
        response = make_response(redirect(url_for('register')))
        response.set_cookie('faculty_id', '', expires=0)
        return response

    # --- NEW LOGIC STARTS HERE ---
    
    # Check for the most recent scan for this faculty member
    last_scan = ScanRecord.query.filter_by(faculty_id=faculty.id).order_by(ScanRecord.scanned_at.desc()).first()
    
    if last_scan:
        time_since_last_scan = datetime.utcnow() - last_scan.scanned_at
        if time_since_last_scan < timedelta(hours=24):
            # If the last scan was within 24 hours, show an error page
            next_scan_time = last_scan.scanned_at + timedelta(hours=24)
            return render_template('already_scanned.html', 
                                   faculty=faculty, 
                                   last_scan=last_scan, 
                                   next_scan_time=next_scan_time)

    # --- NEW LOGIC ENDS HERE ---

    # If no recent scan, proceed to record a new one
    scan_record = ScanRecord(faculty_id=faculty.id)
    db.session.add(scan_record)
    db.session.commit()
    
    latest_scan = {
        'faculty_name': faculty.name,
        'faculty_phone_number': faculty.phone_number,
        'faculty_department': faculty.department,
        'scanned_at': scan_record.scanned_at.strftime('%Y-%m-%d %H:%M:%S'),
        'scan_id': scan_record.id,
        'timestamp': scan_record.scanned_at.timestamp()
    }
    
    return redirect(url_for('scan_success'))

# ... (the rest of your app.py remains the same) ...

@app.route('/scan-success')
def scan_success():
    faculty_id = request.cookies.get('faculty_id')
    if faculty_id:
        faculty = Faculty.query.get(faculty_id)
        if faculty:
            return render_template('scan_success.html', faculty=faculty)
    
    return redirect(url_for('register'))

@app.route('/dashboard')
def dashboard():
    # Get recent scans (last 50)
    recent_scans = db.session.query(ScanRecord, Faculty)\
        .join(Faculty, ScanRecord.faculty_id == Faculty.id)\
        .order_by(ScanRecord.scanned_at.desc())\
        .limit(50).all()
    
    scan_data = []
    for scan_record, faculty in recent_scans:
        scan_data.append({
            'faculty_name': faculty.name,
            'faculty_phone_number': faculty.phone_number,
            'faculty_department': faculty.department,
            'scanned_at': scan_record.scanned_at.strftime('%Y-%m-%d %H:%M:%S'),
            'scan_id': scan_record.id
        })
    
    return render_template('dashboard.html', scans=scan_data)

@app.route('/api/stats')
def stats():
    total_faculty = Faculty.query.count()
    total_scans = ScanRecord.query.count()
    today_scans = ScanRecord.query.filter(
        db.func.date(ScanRecord.scanned_at) == datetime.utcnow().date()
    ).count()
    
    return jsonify({
        'total_faculty': total_faculty,
        'total_scans': total_scans,
        'today_scans': today_scans
    })

@app.route('/api/latest-scan')
def get_latest_scan():
    global latest_scan
    return jsonify(latest_scan if latest_scan else {})

@app.route('/api/recent-scans')
def get_recent_scans():
    # Get recent scans (last 20)
    recent_scans = db.session.query(ScanRecord, Faculty)\
        .join(Faculty, ScanRecord.faculty_id == Faculty.id)\
        .order_by(ScanRecord.scanned_at.desc())\
        .limit(20).all()
    
    scan_data = []
    for scan_record, faculty in recent_scans:
        scan_data.append({
            'faculty_name': faculty.name,
            'faculty_phone_number': faculty.phone_number,
            'faculty_department': faculty.department,
            'scanned_at': scan_record.scanned_at.strftime('%Y-%m-%d %H:%M:%S'),
            'scan_id': scan_record.id,
            'timestamp': scan_record.scanned_at.timestamp()
        })
    
    return jsonify(scan_data)

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)