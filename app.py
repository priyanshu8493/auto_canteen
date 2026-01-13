import os
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
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

# --- Device 2 Database Models (Separate tables for second device) ---
class Faculty2(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(10), unique=True, nullable=False) 
    department = db.Column(db.String(100), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    scan_records = db.relationship('ScanRecord2', backref='faculty', lazy=True)

class ScanRecord2(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    faculty_id = db.Column(db.String(36), db.ForeignKey('faculty2.id'), nullable=False)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)

class MealCounter2(db.Model):
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

# --- Helper functions for Device 2 ---
def get_meal_counter2():
    counter = MealCounter2.query.first()
    if not counter:
        counter = MealCounter2(count=0)
        db.session.add(counter)
        db.session.commit()
    return counter

def increment_meal_counter2():
    counter = get_meal_counter2()
    counter.count += 1
    db.session.commit()
    return counter.count

def get_latest_scan_from_db2():
    latest_scan_record = ScanRecord2.query.join(Faculty2).order_by(ScanRecord2.scanned_at.desc()).first()
    if latest_scan_record:
        faculty = Faculty2.query.get(latest_scan_record.faculty_id)
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

        # Enforce a 6-hour cooldown between scans to prevent duplicates
        cooldown = timedelta(hours=6)
        window_start = datetime.utcnow() - cooldown
        # Check for any scan within the cooldown window
        recent_scan = ScanRecord.query.filter(ScanRecord.faculty_id == faculty.id, ScanRecord.scanned_at >= window_start).order_by(ScanRecord.scanned_at.desc()).first()
        if recent_scan:
            time_since_last_scan = datetime.utcnow() - recent_scan.scanned_at
            next_scan_time = recent_scan.scanned_at + cooldown
            print(f"Scan blocked for faculty {faculty.id} ({faculty.name}). Last scan at {recent_scan.scanned_at}, {time_since_last_scan} ago. Next allowed at {next_scan_time}")
            return render_template('already_scanned.html', faculty=faculty, last_scan=recent_scan, next_scan_time=next_scan_time)

        # No recent scan found in the cooldown window; create a new scan record
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
        
        # Emit to all connected clients on default namespace
        socketio.emit('new_scan', latest_scan_data, namespace='/')
        
        # Increment counter and emit update
        current_count = increment_meal_counter()
        socketio.emit('counter_update', {'count': current_count}, namespace='/')
        
        # Redirect to scan success with the created scan id so we can show timestamp
        return redirect(url_for('scan_success', scan_id=scan_record.id, _external=False))
        
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
            # Optionally show the recorded scan timestamp in IST if provided via query param
            scan_id = request.args.get('scan_id')
            scanned_at_ist = None
            if scan_id:
                scan_record = ScanRecord.query.get(scan_id)
                if scan_record and scan_record.scanned_at:
                    # The DB timestamp is UTC (naive), mark as UTC then convert to IST
                    scanned_utc = scan_record.scanned_at.replace(tzinfo=timezone.utc)
                    scanned_ist_dt = scanned_utc.astimezone(ZoneInfo('Asia/Kolkata'))
                    scanned_at_ist = scanned_ist_dt.strftime('%Y-%m-%d %I:%M %p')
            return render_template('scan_success.html', faculty=faculty, scanned_at_ist=scanned_at_ist)
    return redirect(url_for('register', _external=False))

# --- Device 2 Routes (Completely separate from Device 1) ---
@app.route('/register2', methods=['GET', 'POST'])
def register2():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            phone_number = request.form.get('phone_number', '').strip()
            department = request.form.get('department', '').strip()

            if not all([name, phone_number, department]):
                return render_template('register.html', error="All fields are required")

            existing_faculty = Faculty2.query.filter_by(phone_number=phone_number).first()
            if existing_faculty:
                response = make_response(redirect(url_for('register2_success', _external=False)))
                response.set_cookie('faculty_id_2', existing_faculty.id, max_age=60*60*24*365, secure=True, httponly=True, samesite='Lax')
                return response

            faculty = Faculty2(name=name, phone_number=phone_number, department=department)
            db.session.add(faculty)
            db.session.commit()

            response = make_response(redirect(url_for('register2_success', _external=False)))
            response.set_cookie('faculty_id_2', faculty.id, max_age=60*60*24*365, secure=True, httponly=True, samesite='Lax')
            return response
            
        except Exception as e:
            db.session.rollback()
            return render_template('register.html', error="Registration failed. Please try again.")

    return render_template('register.html')

@app.route('/register2-success')
def register2_success():
    faculty_id = request.cookies.get('faculty_id_2')
    if faculty_id:
        faculty = Faculty2.query.get(faculty_id)
        if faculty:
            return render_template('register_success.html', faculty=faculty)
    return redirect(url_for('register2', _external=False))

@app.route('/scan2')
def scan2():
    try:
        faculty_id = request.cookies.get('faculty_id_2')
        
        if not faculty_id:
            return redirect(url_for('register2', _external=False))
        
        faculty = Faculty2.query.get(faculty_id)
        if not faculty:
            response = make_response(redirect(url_for('register2', _external=False)))
            response.set_cookie('faculty_id_2', '', expires=0)
            return response

        # Enforce a 6-hour cooldown between scans to prevent duplicates
        cooldown = timedelta(hours=6)
        window_start = datetime.utcnow() - cooldown
        # Check for any scan within the cooldown window
        recent_scan = ScanRecord2.query.filter(ScanRecord2.faculty_id == faculty.id, ScanRecord2.scanned_at >= window_start).order_by(ScanRecord2.scanned_at.desc()).first()
        if recent_scan:
            time_since_last_scan = datetime.utcnow() - recent_scan.scanned_at
            next_scan_time = recent_scan.scanned_at + cooldown
            print(f"Scan blocked for faculty {faculty.id} ({faculty.name}). Last scan at {recent_scan.scanned_at}, {time_since_last_scan} ago. Next allowed at {next_scan_time}")
            return render_template('already_scanned.html', faculty=faculty, last_scan=recent_scan, next_scan_time=next_scan_time)

        # No recent scan found in the cooldown window; create a new scan record
        scan_record = ScanRecord2(faculty_id=faculty.id)
        db.session.add(scan_record)
        db.session.commit()
        
        # Emit socket events for real-time updates on device 2 namespace
        latest_scan_data = {
            'faculty_name': faculty.name,
            'faculty_phone_number': faculty.phone_number,
            'faculty_department': faculty.department,
            'scanned_at': scan_record.scanned_at.strftime('%Y-%m-%d %H:%M:%S'),
            'scan_id': scan_record.id,
            'timestamp': scan_record.scanned_at.timestamp()
        }
        
        # Emit to device 2 namespace only
        socketio.emit('new_scan', latest_scan_data, namespace='/device2')
        
        # Increment counter and emit update
        current_count = increment_meal_counter2()
        socketio.emit('counter_update', {'count': current_count}, namespace='/device2')
        
        # Redirect to scan success with the created scan id so we can show timestamp
        return redirect(url_for('scan2_success', scan_id=scan_record.id, _external=False))
        
    except Exception as e:
        # Rollback DB changes and log full traceback for debugging
        db.session.rollback()
        import traceback
        tb = traceback.format_exc()
        # Print traceback to console (visible in systemd or process output)
        print("--- Scan2 route exception traceback ---")
        print(tb)
        # Also append traceback to a log file for later inspection
        try:
            with open(os.path.join(os.path.dirname(__file__), 'auto_canteen.log'), 'a') as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] Scan2 exception: {str(e)}\n")
                lf.write(tb + "\n")
        except Exception as log_e:
            print('Failed to write to auto_canteen.log:', log_e)

        # Return a helpful message containing the exception (temporary for debugging)
        # NOTE: remove or sanitize detailed exception messages in production
        return render_template('success.html', title="Scan Error", message=f"Scan failed: {str(e)}")

@app.route('/scan2-success')
def scan2_success():
    faculty_id = request.cookies.get('faculty_id_2')
    if faculty_id:
        faculty = Faculty2.query.get(faculty_id)
        if faculty:
            # Optionally show the recorded scan timestamp in IST if provided via query param
            scan_id = request.args.get('scan_id')
            scanned_at_ist = None
            if scan_id:
                scan_record = ScanRecord2.query.get(scan_id)
                if scan_record and scan_record.scanned_at:
                    # The DB timestamp is UTC (naive), mark as UTC then convert to IST
                    scanned_utc = scan_record.scanned_at.replace(tzinfo=timezone.utc)
                    scanned_ist_dt = scanned_utc.astimezone(ZoneInfo('Asia/Kolkata'))
                    scanned_at_ist = scanned_ist_dt.strftime('%Y-%m-%d %I:%M %p')
            return render_template('scan_success.html', faculty=faculty, scanned_at_ist=scanned_at_ist)
    return redirect(url_for('register2', _external=False))

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
        return render_template('success.html', title="Error", message="Failed to load counter")

@app.route("/counter2")
def show_counter2():
    try:
        counter = get_meal_counter2()
        return render_template("counter2.html", count=counter.count)
    except Exception as e:
        return render_template('success.html', title="Error", message="Failed to load counter2")

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

@app.route("/api/counter2")
def api_counter2():
    try:
        counter = get_meal_counter2()
        return jsonify({"count": counter.count})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch counter2'}), 500

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

@app.route("/reset-counter2", methods=["POST"])
def reset_counter2():
    try:
        counter = get_meal_counter2()
        counter.count = 0
        counter.last_reset = datetime.utcnow()
        db.session.commit()
        
        # Emit counter reset to device2 namespace only
        socketio.emit('counter_update', {'count': 0}, namespace='/device2')
        return redirect(url_for("show_counter2", _external=False))
    except Exception as e:
        db.session.rollback()
        return render_template('success.html', title="Error", message="Failed to reset counter2")

@app.route("/api/speak")
def api_speak():
    """Generate speech audio using system text-to-speech with proper Raspberry Pi support"""
    try:
        text = request.args.get('text', 'Error')
        
        # Try to use available TTS systems
        import subprocess
        import tempfile
        
        # Try espeak first (most common on Raspberry Pi)
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_file = f.name
            
            # Use espeak with optimized settings for Raspberry Pi
            # -a: amplitude (0-200), -p: pitch (0-99), -s: speed (wpm)
            # Added explicit UTF-8 handling for compatibility
            espeak_cmd = ['espeak', '-w', temp_file, '-a', '200', '-s', '150', text]
            print(f"TTS: Running espeak command: {' '.join(espeak_cmd)}")
            
            subprocess.run(
                espeak_cmd,
                check=True,
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Verify file was created and has content
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                print("ERROR: espeak generated empty file")
                raise subprocess.CalledProcessError(1, 'espeak')
            
            # Read and return the audio file
            with open(temp_file, 'rb') as f:
                audio_data = f.read()
            
            print(f"TTS: Successfully generated {len(audio_data)} bytes of audio via espeak")
            
            # Clean up temp file
            os.unlink(temp_file)
            
            from flask import send_file
            from io import BytesIO
            # CRITICAL: Ensure audio plays immediately without caching
            response = send_file(
                BytesIO(audio_data),
                mimetype='audio/wav',
                as_attachment=False,
                download_name='speech.wav'
            )
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
            print(f"WARNING: espeak failed: {e}")
            # espeak not available or failed, try festival
            try:
                with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
                    temp_file = f.name
                    # Format text for festival
                    f.write(f'(SayText "{text}")')
                
                # Use festival text2wave converter
                output_file = temp_file.replace('.txt', '.wav')
                festival_cmd = ['text2wave', temp_file, '-o', output_file]
                print(f"TTS: Running festival command: {' '.join(festival_cmd)}")
                
                subprocess.run(
                    festival_cmd,
                    check=True,
                    timeout=15,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                    print("ERROR: festival generated empty file")
                    raise subprocess.CalledProcessError(1, 'text2wave')
                
                with open(output_file, 'rb') as f:
                    audio_data = f.read()
                
                print(f"TTS: Successfully generated {len(audio_data)} bytes of audio via festival")
                
                # Clean up temp files
                os.unlink(temp_file)
                os.unlink(output_file)
                
                from flask import send_file
                from io import BytesIO
                response = send_file(
                    BytesIO(audio_data),
                    mimetype='audio/wav',
                    as_attachment=False,
                    download_name='speech.wav'
                )
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
                
            except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
                print(f"WARNING: festival also failed: {e}")
                # Clean up if files exist
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        # If we get here, no TTS system is available
        print("CRITICAL: No TTS system available (espeak and festival not installed)")
        print("On Raspberry Pi, install with: sudo apt-get install espeak espeak-ng")
        return jsonify({'error': 'TTS not available - install espeak with: sudo apt-get install espeak'}), 501
        
    except Exception as e:
        import traceback
        print(f"TTS error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'TTS generation failed: {str(e)}'}), 500

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    # Send current counter value to newly connected client
    emit('counter_update', {'count': get_meal_counter().count})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

# Socket.IO event handlers for Device 2 (separate namespace)
@socketio.on('connect', namespace='/device2')
def handle_connect_device2():
    print(f"Device2 client connected: {request.sid}")
    # Send current counter value to newly connected device2 client
    emit('counter_update', {'count': get_meal_counter2().count}, namespace='/device2')

@socketio.on('disconnect', namespace='/device2')
def handle_disconnect_device2():
    print(f"Device2 client disconnected: {request.sid}")

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
