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
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    # Ensure Socket.IO works with Nginx reverse proxy
    ping_timeout=60,
    ping_interval=25,
    engineio_logger=False,
    socketio_logger=False
)

# --- WSGI Middleware for subpath handling and reverse proxy support ---
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
        
        # Handle reverse proxy headers for HTTPS detection
        # This is crucial for Nginx + Cloudflare setups
        if 'HTTP_X_FORWARDED_PROTO' in environ:
            environ['wsgi.url_scheme'] = environ['HTTP_X_FORWARDED_PROTO']
        
        if 'HTTP_X_FORWARDED_FOR' in environ:
            environ['REMOTE_ADDR'] = environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
        
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
    # Note: Cloudflare always uses HTTPS, so we don't force redirect
    proto = request.headers.get('X-Forwarded-Proto', request.scheme)
    if proto == 'http' and not app.debug:
        # Only redirect in production if explicitly on http
        secure_url = request.url.replace('http://', 'https://', 1)
        return redirect(secure_url, code=301)

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

        # NOTE: 24-hour scan constraint removed to allow multiple scans per day
        # Previous constraint code:
        # last_scan = ScanRecord.query.filter_by(faculty_id=faculty.id).order_by(ScanRecord.scanned_at.desc()).first()
        # if last_scan:
        #     time_since_last_scan = datetime.utcnow() - last_scan.scanned_at
        #     if time_since_last_scan < timedelta(hours=24):
        #         return render_template('already_scanned.html', ...)

        # Double-check right before creating the record to reduce race-condition window
        latest_scan_check = ScanRecord.query.filter(ScanRecord.faculty_id == faculty.id, ScanRecord.scanned_at >= window_start).order_by(ScanRecord.scanned_at.desc()).first()
        if latest_scan_check:
            time_since_last_scan = datetime.utcnow() - latest_scan_check.scanned_at
            next_scan_time = latest_scan_check.scanned_at + cooldown
            print(f"Scan blocked at last-moment check for faculty {faculty.id} ({faculty.name}). Last scan at {latest_scan_check.scanned_at}")
            return render_template('already_scanned.html', faculty=faculty, last_scan=latest_scan_check, next_scan_time=next_scan_time)

        scan_record = ScanRecord(faculty_id=faculty.id)
        db.session.add(scan_record)
        db.session.commit()
        
        # Emit socket events for real-time updates
        latest_scan_data = {
            'faculty_name': faculty.name,
            'faculty_phone_number': faculty.phone_number,
            'faculty_department': faculty.department,
            'scanned_at': scan_record.scanned_at.strftime('%Y-%m-%d %H:%M:%S'),
            'scan_id': scan_record.id,
            'timestamp': scan_record.scanned_at.timestamp()
        }
        
        # Emit to all connected clients
        socketio.emit('new_scan', latest_scan_data, namespace='/')
        
        # Increment counter and emit update
        current_count = increment_meal_counter()
        socketio.emit('counter_update', {'count': current_count}, namespace='/')
        
        return redirect(url_for('scan_success', _external=False))
        
    except Exception as e:
        # Rollback DB changes and log full traceback for debugging
        db.session.rollback()
        import traceback
        tb = traceback.format_exc()
        # Print traceback to console (visible in systemd or process output)
        print("--- Scan route exception traceback ---")
        print(tb)
        # Also append traceback to a log file for later inspection
        try:
            with open(os.path.join(os.path.dirname(__file__), 'auto_canteen.log'), 'a') as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] Scan exception: {str(e)}\n")
                lf.write(tb + "\n")
        except Exception as log_e:
            print('Failed to write to auto_canteen.log:', log_e)

        # Return a helpful message containing the exception (temporary for debugging)
        # NOTE: remove or sanitize detailed exception messages in production
        return render_template('success.html', title="Scan Error", message=f"Scan failed: {str(e)}")

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
        print("Dashboard accessed")  # Debug log
        
        # Test database connection
        faculty_count = Faculty.query.count()
        scan_count = ScanRecord.query.count()
        print(f"Faculty count: {faculty_count}, Scan count: {scan_count}")  # Debug log
        
        recent_scans = db.session.query(ScanRecord, Faculty)\
            .join(Faculty, ScanRecord.faculty_id == Faculty.id)\
            .order_by(ScanRecord.scanned_at.desc())\
            .limit(50).all()
        
        print(f"Found {len(recent_scans)} recent scans")  # Debug log
        
        scan_data = [{'faculty_name': f.name, 'faculty_phone_number': f.phone_number, 'faculty_department': f.department, 'scanned_at': sr.scanned_at.strftime('%Y-%m-%d %H:%M:%S'), 'scan_id': sr.id} for sr, f in recent_scans]
        
        return render_template('dashboard.html', scans=scan_data)
    except Exception as e:
        print(f"Dashboard error: {e}")  # Debug log
        return render_template('success.html', title="Error", message=str(e))

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
        # Enforce a 6-hour cooldown between scans to prevent duplicates
        # Check if any scan exists for this faculty within the cooldown window
        cooldown = timedelta(hours=6)
        window_start = datetime.utcnow() - cooldown
        recent_scan = ScanRecord.query.filter(ScanRecord.faculty_id == faculty.id, ScanRecord.scanned_at >= window_start).order_by(ScanRecord.scanned_at.desc()).first()
        if recent_scan:
            time_since_last_scan = datetime.utcnow() - recent_scan.scanned_at
            next_scan_time = recent_scan.scanned_at + cooldown
            # Log helpful debug info
            print(f"Scan blocked for faculty {faculty.id} ({faculty.name}). Last scan at {recent_scan.scanned_at}, {time_since_last_scan} ago. Next allowed at {next_scan_time}")
            return render_template('already_scanned.html', faculty=faculty, last_scan=recent_scan, next_scan_time=next_scan_time)
@app.route("/counter")
def show_counter():
    try:
        counter = get_meal_counter()
        return render_template("counter.html", count=counter.count)
    except Exception as e:
        return render_template('success.html', title="Error", message="Failed to load counter")

@app.route("/audio-diagnostic")
def audio_diagnostic():
    try:
        return render_template("audio_diagnostic.html")
    except Exception as e:
        return render_template('success.html', title="Error", message="Failed to load audio diagnostic")

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
        
        # Emit counter reset to all connected clients
        socketio.emit('counter_update', {'count': 0}, namespace='/')
        return redirect(url_for("show_counter", _external=False))
    except Exception as e:
        db.session.rollback()
        return render_template('success.html', title="Error", message="Failed to reset counter")

@app.route("/api/speak")
def api_speak():
    """Generate speech audio using system text-to-speech"""
    try:
        text = request.args.get('text', 'Error')
        
        # Try to use available TTS systems
        import subprocess
        import tempfile
        
        # Try espeak first (most common on Raspberry Pi)
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_file = f.name
            
            # Use espeak to generate speech
            subprocess.run(['espeak', '-w', temp_file, text], check=True, timeout=10)
            
            # Read and return the audio file
            with open(temp_file, 'rb') as f:
                audio_data = f.read()
            
            # Clean up temp file
            os.unlink(temp_file)
            
            from flask import send_file
            from io import BytesIO
            return send_file(BytesIO(audio_data), mimetype='audio/wav', cache_timeout=0)
        
        except (subprocess.CalledProcessError, FileNotFoundError):
            # espeak not available, try festival
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    temp_file = f.name
                
                # Use festival to generate speech
                subprocess.run(['festival', '--tts'], input=text.encode(), check=True, timeout=10)
                
                # If festival succeeds but doesn't output to file, try text2wave
                try:
                    with open(temp_file, 'w') as f:
                        f.write(f"(SayText \"{text}\")")
                    
                    subprocess.run(
                        ['text2wave', temp_file, '-o', temp_file + '.wav'],
                        check=True,
                        timeout=10
                    )
                    
                    with open(temp_file + '.wav', 'rb') as f:
                        audio_data = f.read()
                    
                    os.unlink(temp_file)
                    os.unlink(temp_file + '.wav')
                    
                    from flask import send_file
                    from io import BytesIO
                    return send_file(BytesIO(audio_data), mimetype='audio/wav', cache_timeout=0)
                except:
                    pass
                
                os.unlink(temp_file)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        # If we get here, no TTS system is available
        print("WARNING: No TTS system available (espeak or festival not installed)")
        return jsonify({'error': 'TTS not available'}), 501
        
    except Exception as e:
        print(f"TTS error: {e}")
        return jsonify({'error': 'TTS generation failed'}), 500

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    # Send current counter value to newly connected client
    emit('counter_update', {'count': get_meal_counter().count})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

# Initialize database
with app.app_context():
    try:
        db.create_all()
        # Ensure counter exists
        get_meal_counter()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

if __name__ == '__main__':
    socketio.run(app, debug=os.environ.get('DEBUG', 'False').lower() == 'true', 
                 host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
