import os
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///canteen.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure for subpath deployment
APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/auto_canteen')
app.config['APPLICATION_ROOT'] = APPLICATION_ROOT
app.config['PREFERRED_URL_SCHEME'] = 'https'

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- WSGI Middleware for subpath handling ---
class ReverseProxied:
    def __init__(self, app, script_name=None):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        script_name = self.script_name or APPLICATION_ROOT
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
        return self.app(environ, start_response)

app.wsgi_app = ReverseProxied(app.wsgi_app, APPLICATION_ROOT)

# --- Database Models ---
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

class MealCounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=0)
    last_reset = db.Column(db.DateTime, default=datetime.utcnow)

# --- Helper functions ---
def get_meal_counter():
    counter = MealCounter.query.first()
    if not counter:
        counter = MealCounter(count=0)
        db.session.add(counter)
        db.session.commit()
    return counter

def increment_meal_counter():
    counter = get_meal_counter()
    counter.count += 1
    db.session.commit()
    return counter.count

def get_latest_scan_from_db():
    latest_scan_record = ScanRecord.query.join(Faculty).order_by(ScanRecord.scanned_at.desc()).first()
    if latest_scan_record:
        faculty = Faculty.query.get(latest_scan_record.faculty_id)
        return {
            'faculty_name': faculty.name,
            'faculty_phone_number': faculty.phone_number,
            'faculty_department': faculty.department,
            'scanned_at': latest_scan_record.scanned_at.strftime('%Y-%m-%d %H:%M:%S'),
            'scan_id': latest_scan_record.id,
            'timestamp': latest_scan_record.scanned_at.timestamp()
        }
    return None

@app.before_request
def before_request():
    # Handle reverse proxy and ensure proper URL generation
    if request.headers.get('X-Forwarded-Proto') == 'http':
        return redirect(request.url.replace('http://', 'https://', 1), code=301)

# --- Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            phone_number = request.form.get('phone_number', '').strip()
            department = request.form.get('department', '').strip()

            if not all([name, phone_number, department]):
                return render_template('register.html', error="All fields are required")

            existing_faculty = Faculty.query.filter_by(phone_number=phone_number).first()
            if existing_faculty:
                response = make_response(redirect(url_for('register_success', _external=False)))
                response.set_cookie('faculty_id', existing_faculty.id, max_age=60*60*24*365, secure=True, httponly=True, samesite='Lax')
                return response

            faculty = Faculty(name=name, phone_number=phone_number, department=department)
            db.session.add(faculty)
            db.session.commit()

            response = make_response(redirect(url_for('register_success', _external=False)))
            response.set_cookie('faculty_id', faculty.id, max_age=60*60*24*365, secure=True, httponly=True, samesite='Lax')
            return response
            
        except Exception as e:
            db.session.rollback()
            return render_template('register.html', error="Registration failed. Please try again.")

    return render_template('register.html')

@app.route('/register-success')
def register_success():
    faculty_id = request.cookies.get('faculty_id')
    if faculty_id:
        faculty = Faculty.query.get(faculty_id)
        if faculty:
            return render_template('register_success.html', faculty=faculty)
    return redirect(url_for('register', _external=False))

@app.route('/scan')
def scan():
    try:
        faculty_id = request.cookies.get('faculty_id')
        
        if not faculty_id:
            return redirect(url_for('register', _external=False))
        
        faculty = Faculty.query.get(faculty_id)
        if not faculty:
            response = make_response(redirect(url_for('register', _external=False)))
            response.set_cookie('faculty_id', '', expires=0)
            return response

        last_scan = ScanRecord.query.filter_by(faculty_id=faculty.id).order_by(ScanRecord.scanned_at.desc()).first()
        
        if last_scan:
            time_since_last_scan = datetime.utcnow() - last_scan.scanned_at
            if time_since_last_scan < timedelta(hours=24):
                next_scan_time = last_scan.scanned_at + timedelta(hours=24)
                return render_template('already_scanned.html', faculty=faculty, last_scan=last_scan, next_scan_time=next_scan_time)

        scan_record = ScanRecord(faculty_id=faculty.id)
        db.session.add(scan_record)
        db.session.commit()
        
        # Emit socket event for real-time updates
        latest_scan_data = {
            'faculty_name': faculty.name,
            'faculty_phone_number': faculty.phone_number,
            'faculty_department': faculty.department,
            'scanned_at': scan_record.scanned_at.strftime('%Y-%m-%d %H:%M:%S'),
            'scan_id': scan_record.id,
            'timestamp': scan_record.scanned_at.timestamp()
        }
        
        socketio.emit('new_scan', latest_scan_data)
        
        # Increment counter
        current_count = increment_meal_counter()
        socketio.emit('counter_update', {'count': current_count})
        
        return redirect(url_for('scan_success', _external=False))
        
    except Exception as e:
        db.session.rollback()
        return render_template('error.html', error="Scan failed. Please try again.")

@app.route('/scan-success')
def scan_success():
    faculty_id = request.cookies.get('faculty_id')
    if faculty_id:
        faculty = Faculty.query.get(faculty_id)
        if faculty:
            return render_template('scan_success.html', faculty=faculty)
    return redirect(url_for('register', _external=False))

@app.route('/dashboard')
def dashboard():
    try:
        recent_scans = db.session.query(ScanRecord, Faculty)\
            .join(Faculty, ScanRecord.faculty_id == Faculty.id)\
            .order_by(ScanRecord.scanned_at.desc())\
            .limit(50).all()
        
        scan_data = [{'faculty_name': f.name, 'faculty_phone_number': f.phone_number, 'faculty_department': f.department, 'scanned_at': sr.scanned_at.strftime('%Y-%m-%d %H:%M:%S'), 'scan_id': sr.id} for sr, f in recent_scans]
        return render_template('dashboard.html', scans=scan_data)
    except Exception as e:
        return render_template('error.html', error="Failed to load dashboard")

@app.route('/api/stats')
def stats():
    try:
        return jsonify({
            'total_faculty': Faculty.query.count(),
            'total_scans': ScanRecord.query.count(),
            'today_scans': ScanRecord.query.filter(db.func.date(ScanRecord.scanned_at) == datetime.utcnow().date()).count()
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch stats'}), 500

@app.route('/api/latest-scan')
def get_latest_scan():
    try:
        latest_scan = get_latest_scan_from_db()
        return jsonify(latest_scan if latest_scan else {})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch latest scan'}), 500

@app.route('/api/recent-scans')
def get_recent_scans():
    try:
        recent_scans = db.session.query(ScanRecord, Faculty)\
            .join(Faculty, ScanRecord.faculty_id == Faculty.id)\
            .order_by(ScanRecord.scanned_at.desc())\
            .limit(20).all()
        scan_data = [{'faculty_name': f.name, 'faculty_phone_number': f.phone_number, 'faculty_department': f.department, 'scanned_at': sr.scanned_at.strftime('%Y-%m-%d %H:%M:%S'), 'scan_id': sr.id, 'timestamp': sr.scanned_at.timestamp()} for sr, f in recent_scans]
        return jsonify(scan_data)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch recent scans'}), 500

@app.route("/counter")
def show_counter():
    try:
        counter = get_meal_counter()
        return render_template("counter.html", count=counter.count)
    except Exception as e:
        return render_template('error.html', error="Failed to load counter")

@app.route("/api/counter")
def api_counter():
    try:
        counter = get_meal_counter()
        return jsonify({"count": counter.count})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch counter'}), 500

@app.route("/reset-counter", methods=["POST"])
def reset_counter():
    try:
        counter = get_meal_counter()
        counter.count = 0
        counter.last_reset = datetime.utcnow()
        db.session.commit()
        
        socketio.emit('counter_update', {'count': 0})
        return redirect(url_for("show_counter", _external=False))
    except Exception as e:
        db.session.rollback()
        return render_template('error.html', error="Failed to reset counter")

@socketio.on('connect')
def handle_connect():
    emit('counter_update', {'count': get_meal_counter().count})

# Initialize database
with app.app_context():
    try:
        db.create_all()
        # Ensure counter exists
        get_meal_counter()
    except Exception as e:
        print(f"Database initialization error: {e}")

if __name__ == '__main__':
    socketio.run(app, debug=os.environ.get('DEBUG', 'False').lower() == 'true', 
                 host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
