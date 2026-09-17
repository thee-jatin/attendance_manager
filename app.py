from datetime import datetime, timedelta
import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
CORS(app)

CLASSROOM_QR_TOKENS = ["ATTANDANCE_MARK", "ATTENDANCE_MARK"]
DEFAULT_SESSION_DURATION = 600

def get_db_connection():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Teachers table with subject column
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            subject TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT,
            teacher_name TEXT,
            subject TEXT,
            lecture TEXT,
            start_time TEXT,
            expiry_time TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT,
            subject TEXT,
            date TEXT,
            time_marked TEXT,
            status TEXT,
            session_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/api/teacher/login', methods=['POST', 'OPTIONS'])
def teacher_login():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    data = request.get_json() or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()

    conn = get_db_connection()
    teacher = conn.execute('SELECT * FROM teachers WHERE username = ?', (username,)).fetchone()
    conn.close()

    if teacher and check_password_hash(teacher['password'], password):
        return jsonify({
            'status': 'success',
            'teacher_id': teacher['username'],
            'name': teacher['name'],
            'subject': teacher['subject']
        }), 200
    return jsonify({'status': 'fail', 'message': 'Invalid Teacher ID or Password!'}), 401


# ------------------------------------------------------------------
# THIS ROUTE WAS MISSING — student_login.html calls it but the
# backend had no handler for it, so student login could never
# succeed in the first place.
# ------------------------------------------------------------------
@app.route('/api/student/login', methods=['POST', 'OPTIONS'])
def student_login():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    data = request.get_json() or {}
    roll_no = str(data.get('roll_no', '')).strip()
    password = str(data.get('password', '')).strip()

    if not roll_no or not password:
        return jsonify({'status': 'fail', 'message': 'Roll number and password required!'}), 400

    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE roll_no = ?', (roll_no,)).fetchone()
    conn.close()

    if student and student['password'] and check_password_hash(student['password'], password):
        return jsonify({
            'status': 'success',
            'roll_no': student['roll_no'],
            'name': student['name']
        }), 200

    return jsonify({'status': 'fail', 'message': 'Invalid Roll Number or Password!'}), 401


@app.route('/api/teacher/start-session', methods=['POST', 'OPTIONS'])
def start_session():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    data = request.get_json() or {}
    teacher_id = data.get('teacher_id', '')
    teacher_name = data.get('teacher_name', '')
    subject = data.get('subject', '')
    lecture = data.get('lecture', '')
    duration_seconds = int(data.get('duration_seconds', DEFAULT_SESSION_DURATION))

    start_time = datetime.now()
    expiry_time = start_time + timedelta(seconds=duration_seconds)

    conn = get_db_connection()
    # Expire old sessions for this specific subject
    conn.execute("UPDATE attendance_sessions SET status = 'expired' WHERE subject = ? AND status = 'active'", (subject,))
    
    conn.execute('''
        INSERT INTO attendance_sessions (teacher_id, teacher_name, subject, lecture, start_time, expiry_time, status)
        VALUES (?, ?, ?, ?, ?, ?, 'active')
    ''', (teacher_id, teacher_name, subject, lecture, start_time.isoformat(), expiry_time.isoformat()))
    
    conn.commit()
    conn.close()

    return jsonify({
        'status': 'success',
        'message': 'Session started successfully',
        'expires_in_seconds': duration_seconds
    }), 200

@app.route('/api/teacher/live-records', methods=['GET', 'OPTIONS'])
def get_live_records():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    subject = request.args.get('subject', '').strip()
    # NEW: optional ?date=YYYY-MM-DD param. Agar diya hai toh usi date ka
    # data dikhao (purana attendance data database mein already safe hai,
    # sirf yeh naya filter usse dekhne ka rasta deta hai). Agar nahi diya
    # toh purana behaviour (aaj ki date) waisa hi rahega.
    requested_date = request.args.get('date', '').strip()
    today = requested_date if requested_date else datetime.now().strftime('%Y-%m-%d')

    if not subject:
        return jsonify({'status': 'error', 'message': 'Subject parameter missing!'}), 400

    conn = get_db_connection()
    # Fetch attendance ONLY for this teacher's specific subject
    query = '''
        SELECT s.roll_no, s.name, 
               COALESCE(a.date, ?) as date,
               COALESCE(a.time_marked, '--') as time_marked,
               COALESCE(a.status, 'Pending') as status
        FROM students s
        LEFT JOIN attendance a ON s.roll_no = a.roll_no AND a.subject = ? AND a.date = ?
        ORDER BY s.roll_no ASC
    '''
    records = conn.execute(query, (today, subject, today)).fetchall()
    conn.close()
    return jsonify({'status': 'success', 'data': [dict(row) for row in records]}), 200

@app.route('/api/teacher/manual-override', methods=['POST', 'OPTIONS'])
def manual_override():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    data = request.get_json() or {}
    roll_no = data.get('roll_no')
    subject = data.get('subject')

    if not roll_no or not subject:
        return jsonify({'status': 'error', 'message': 'Roll number and Subject required'}), 400

    today = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%I:%M:%S %p')

    conn = get_db_connection()
    existing = conn.execute('SELECT * FROM attendance WHERE roll_no = ? AND subject = ? AND date = ?', (roll_no, subject, today)).fetchone()

    if existing:
        conn.execute("UPDATE attendance SET status = 'Present', time_marked = ? WHERE roll_no = ? AND subject = ? AND date = ?", (current_time, roll_no, subject, today))
    else:
        conn.execute("INSERT INTO attendance (roll_no, subject, date, time_marked, status) VALUES (?, ?, ?, ?, 'Present')", (roll_no, subject, today, current_time))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': f'Roll No {roll_no} marked Present!'}), 200

@app.route('/api/student/mark-attendance', methods=['POST', 'OPTIONS'])
def mark_attendance():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        data = request.get_json() or {}
        roll_no = str(data.get('roll_no', '')).strip()
        # Normalize: remove all whitespace/newlines and uppercase, so tiny
        # differences in how the QR was generated (spaces, line breaks,
        # lower-case) don't cause a false "Invalid QR" error.
        scanned_token = str(data.get('token', '')).strip().upper().replace(' ', '').replace('\n', '')

        if not roll_no:
            return jsonify({'status': 'error', 'message': 'Student Roll Number missing!'}), 400

        conn = get_db_connection()

        session = conn.execute("SELECT * FROM attendance_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1").fetchone()
        if not session or datetime.now() > datetime.fromisoformat(session['expiry_time']):
            conn.close()
            return jsonify({'status': 'error', 'message': 'Active session nahi mila! Teacher ko bolo session start karein.'}), 403

        normalized_valid_tokens = [t.upper().replace(' ', '') for t in CLASSROOM_QR_TOKENS]
        if scanned_token not in normalized_valid_tokens:
            conn.close()
            print(f'QR mismatch! Scanned (normalized): "{scanned_token}" | Expected one of: {normalized_valid_tokens}')
            return jsonify({'status': 'error', 'message': 'Invalid QR Code!'}), 400

        student = conn.execute('SELECT * FROM students WHERE roll_no = ?', (roll_no,)).fetchone()
        if not student:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Student record not found!'}), 404

        already_marked = conn.execute('SELECT * FROM attendance WHERE roll_no = ? AND session_id = ?', (roll_no, session['id'])).fetchone()
        if already_marked:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Is session ki attendance pehle se marked hai!'}), 409

        timestamp_date = datetime.now().strftime('%Y-%m-%d')
        timestamp_time = datetime.now().strftime('%I:%M:%S %p')

        conn.execute('''
            INSERT INTO attendance (roll_no, subject, date, time_marked, status, session_id)
            VALUES (?, ?, ?, ?, 'Present', ?)
        ''', (roll_no, session['subject'], timestamp_date, timestamp_time, session['id']))
        
        conn.commit()
        conn.close()

        return jsonify({
            'status': 'success',
            'message': 'Attendance Marked Successfully!',
            'roll_no': roll_no,
            'name': student['name'],
            'time': timestamp_time,
            'subject': session['subject']
        }), 200

    except Exception as e:
        print('Server Error:', e)
        return jsonify({'status': 'error', 'message': 'Server Error!'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)