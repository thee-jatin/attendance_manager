from datetime import datetime, timedelta
import sqlite3
import math
import random

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__, static_folder="templates", static_url_path="")

# When someone opens the site's root URL (e.g. the Render link), serve
# index.html as the homepage. Every other HTML file (teacher_login.html,
# student_dashboard.html, etc.) is also automatically reachable directly
# at its own filename, e.g. https://<your-site>/teacher_login.html,
# because static_folder="templates" + static_url_path="" makes Flask
# serve any file sitting inside the templates/ folder.
@app.route("/")
def home():
    return send_from_directory("templates", "index.html")
CORS(app)


# ============================================================
# SETTINGS
# ============================================================

CLASS_QR_TOKENS = [
    "ATTENDANCE_MARK_CLASS",
    "ATTANDANCE_MARK_CLASS"
]

LAB_QR_TOKENS = [
    "ATTENDANCE_MARK_LAB",
    "ATTANDANCE_MARK_LAB"
]

DEFAULT_SESSION_DURATION = 600

# NEW: 2FA settings — 4-digit dynamic code shown on blackboard,
# expires quickly so it can't be relayed to someone outside class.
DYNAMIC_CODE_VALID_SECONDS = 180  # 3 minutes

# NEW: Geo-fencing — default classroom radius (meters), plus a small
# buffer to tolerate normal GPS drift so genuine boundary-line
# students aren't wrongly rejected.
#
# NOTE ON INDOOR GPS: Multi-story concrete buildings degrade GPS
# accuracy heavily (drift of 50-100m is common), and GPS cannot
# reliably tell floors apart (2D lat/long only, no altitude). So this
# radius is intentionally kept BUILDING-level, not ROOM-level — the
# job of telling rooms/floors apart is left to the physical QR code
# (Factor 1), which only exists in that specific classroom. GPS here
# is just a coarse "are you even near the campus" outer check.
DEFAULT_RADIUS_METERS = 80
GEO_BUFFER_METERS = 40


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():
    conn = sqlite3.connect("attendance.db")
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# SAFE COLUMN MIGRATION HELPER
# (adds a column only if it doesn't already exist — never touches
# or deletes existing data)
# ============================================================

def _ensure_column(conn, table, column, coltype):
    existing_cols = [
        row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    ]
    if column not in existing_cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


# ============================================================
# DISTANCE CALCULATION (Haversine formula)
# Returns distance in meters between two lat/long points.
# ============================================================

def distance_in_meters(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return R * c


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    conn = get_db_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------
    # TEACHERS TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            subject TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # STUDENTS TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT
        )
    """)

    # --------------------------------------------------------
    # ATTENDANCE SESSIONS TABLE
    # --------------------------------------------------------

    cursor.execute("""
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
    """)

    # NEW columns for 2FA (dynamic code) + Geo-Fencing — added safely
    # without touching existing rows/columns.
    _ensure_column(conn, "attendance_sessions", "dynamic_code", "TEXT")
    _ensure_column(conn, "attendance_sessions", "code_expiry", "TEXT")
    _ensure_column(conn, "attendance_sessions", "latitude", "REAL")
    _ensure_column(conn, "attendance_sessions", "longitude", "REAL")
    _ensure_column(conn, "attendance_sessions", "radius_meters", "REAL")
    # NEW: 'class' or 'lab' — decides which physical QR (Class QR vs
    # Lab QR) is valid for this session.
    _ensure_column(conn, "attendance_sessions", "room_type", "TEXT")

    # --------------------------------------------------------
    # ATTENDANCE TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT,
            subject TEXT,
            date TEXT,
            time_marked TEXT,
            status TEXT,
            session_id INTEGER
        )
    """)

    # --------------------------------------------------------
    # CLASS INCHARGE TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_incharges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# TEACHER LOGIN
# ============================================================

@app.route("/api/teacher/login", methods=["POST", "OPTIONS"])
def teacher_login():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json() or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return jsonify({
            "status": "fail",
            "message": "Teacher ID and Password required!"
        }), 400

    conn = get_db_connection()

    teacher = conn.execute(
        "SELECT * FROM teachers WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    if teacher and check_password_hash(teacher["password"], password):

        return jsonify({
            "status": "success",
            "teacher_id": teacher["username"],
            "name": teacher["name"],
            "subject": teacher["subject"]
        }), 200

    return jsonify({
        "status": "fail",
        "message": "Invalid Teacher ID or Password!"
    }), 401


# ============================================================
# STUDENT LOGIN
# ============================================================

@app.route("/api/student/login", methods=["POST", "OPTIONS"])
def student_login():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json() or {}

    roll_no = str(data.get("roll_no", "")).strip()
    password = str(data.get("password", "")).strip()

    if not roll_no or not password:
        return jsonify({
            "status": "fail",
            "message": "Roll number and password required!"
        }), 400

    conn = get_db_connection()

    student = conn.execute(
        "SELECT * FROM students WHERE roll_no = ?",
        (roll_no,)
    ).fetchone()

    conn.close()

    if (
        student
        and student["password"]
        and check_password_hash(student["password"], password)
    ):

        return jsonify({
            "status": "success",
            "roll_no": student["roll_no"],
            "name": student["name"]
        }), 200

    return jsonify({
        "status": "fail",
        "message": "Invalid Roll Number or Password!"
    }), 401


# ============================================================
# CLASS INCHARGE LOGIN
# ============================================================

@app.route("/api/incharge/login", methods=["POST", "OPTIONS"])
def incharge_login():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json() or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return jsonify({
            "status": "fail",
            "message": "Username and Password required!"
        }), 400

    conn = get_db_connection()

    incharge = conn.execute(
        "SELECT * FROM class_incharges WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    if (
        incharge
        and check_password_hash(incharge["password"], password)
    ):

        return jsonify({
            "status": "success",
            "incharge_id": incharge["id"],
            "username": incharge["username"],
            "name": incharge["name"]
        }), 200

    return jsonify({
        "status": "fail",
        "message": "Invalid Class Incharge ID or Password!"
    }), 401


# ============================================================
# TEACHER START ATTENDANCE SESSION
# ============================================================

@app.route("/api/teacher/start-session", methods=["POST", "OPTIONS"])
def start_session():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json() or {}

    teacher_id = str(data.get("teacher_id", "")).strip()
    teacher_name = str(data.get("teacher_name", "")).strip()
    subject = str(data.get("subject", "")).strip()
    lecture = str(data.get("lecture", "")).strip()

    # NEW: 'class' or 'lab' — decides which physical QR is valid
    room_type = str(data.get("room_type", "class")).strip().lower()
    if room_type not in ("class", "lab"):
        room_type = "class"

    # NEW: teacher's own device location becomes the classroom's
    # reference point for geo-fencing — no need to hardcode room
    # coordinates, it's captured fresh every time a session starts.
    try:
        teacher_latitude = float(data.get("latitude"))
        teacher_longitude = float(data.get("longitude"))
    except (TypeError, ValueError):
        teacher_latitude = None
        teacher_longitude = None

    try:
        radius_meters = float(data.get("radius_meters", DEFAULT_RADIUS_METERS))
    except (TypeError, ValueError):
        radius_meters = DEFAULT_RADIUS_METERS

    if radius_meters <= 0:
        radius_meters = DEFAULT_RADIUS_METERS

    try:
        duration_seconds = int(
            data.get(
                "duration_seconds",
                DEFAULT_SESSION_DURATION
            )
        )
    except (TypeError, ValueError):
        duration_seconds = DEFAULT_SESSION_DURATION

    if not subject:
        return jsonify({
            "status": "error",
            "message": "Subject is required!"
        }), 400

    if duration_seconds <= 0:
        duration_seconds = DEFAULT_SESSION_DURATION

    start_time = datetime.now()
    expiry_time = start_time + timedelta(
        seconds=duration_seconds
    )

    # NEW: 4-digit dynamic code, separate (shorter) expiry from the
    # overall session — teacher writes/says this on the blackboard.
    dynamic_code = str(random.randint(1000, 9999))
    code_expiry = start_time + timedelta(seconds=DYNAMIC_CODE_VALID_SECONDS)

    conn = get_db_connection()

    # Expire old active sessions of the same subject
    conn.execute(
        """
        UPDATE attendance_sessions
        SET status = 'expired'
        WHERE subject = ?
        AND status = 'active'
        """,
        (subject,)
    )

    conn.execute(
        """
        INSERT INTO attendance_sessions
        (
            teacher_id,
            teacher_name,
            subject,
            lecture,
            start_time,
            expiry_time,
            status,
            dynamic_code,
            code_expiry,
            latitude,
            longitude,
            radius_meters,
            room_type
        )
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
        """,
        (
            teacher_id,
            teacher_name,
            subject,
            lecture,
            start_time.isoformat(),
            expiry_time.isoformat(),
            dynamic_code,
            code_expiry.isoformat(),
            teacher_latitude,
            teacher_longitude,
            radius_meters,
            room_type
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Session started successfully",
        "expires_in_seconds": duration_seconds,
        "dynamic_code": dynamic_code,
        "code_valid_seconds": DYNAMIC_CODE_VALID_SECONDS,
        "room_type": room_type,
        "geo_fencing_active": teacher_latitude is not None and teacher_longitude is not None,
        "radius_meters": radius_meters
    }), 200


# ============================================================
# TEACHER LIVE RECORDS
# ============================================================

@app.route("/api/teacher/live-records", methods=["GET", "OPTIONS"])
def get_live_records():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    subject = request.args.get("subject", "").strip()

    requested_date = request.args.get("date", "").strip()

    today = (
        requested_date
        if requested_date
        else datetime.now().strftime("%Y-%m-%d")
    )

    if not subject:
        return jsonify({
            "status": "error",
            "message": "Subject parameter missing!"
        }), 400

    conn = get_db_connection()

    query = """
        SELECT
            s.roll_no,
            s.name,
            COALESCE(a.date, ?) AS date,
            COALESCE(a.time_marked, '--') AS time_marked,
            COALESCE(a.status, 'Pending') AS status
        FROM students s

        LEFT JOIN attendance a
            ON s.roll_no = a.roll_no
            AND a.subject = ?
            AND a.date = ?

        ORDER BY s.roll_no ASC
    """

    records = conn.execute(
        query,
        (today, subject, today)
    ).fetchall()

    conn.close()

    return jsonify({
        "status": "success",
        "data": [dict(row) for row in records]
    }), 200


# ============================================================
# TEACHER MANUAL OVERRIDE
# ============================================================

@app.route(
    "/api/teacher/manual-override",
    methods=["POST", "OPTIONS"]
)
def manual_override():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json() or {}

    roll_no = str(data.get("roll_no", "")).strip()
    subject = str(data.get("subject", "")).strip()

    if not roll_no or not subject:
        return jsonify({
            "status": "error",
            "message": "Roll number and Subject required"
        }), 400

    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%I:%M:%S %p")

    conn = get_db_connection()

    existing = conn.execute(
        """
        SELECT *
        FROM attendance
        WHERE roll_no = ?
        AND subject = ?
        AND date = ?
        """,
        (roll_no, subject, today)
    ).fetchone()

    if existing:

        conn.execute(
            """
            UPDATE attendance
            SET status = 'Present',
                time_marked = ?
            WHERE roll_no = ?
            AND subject = ?
            AND date = ?
            """,
            (
                current_time,
                roll_no,
                subject,
                today
            )
        )

    else:

        conn.execute(
            """
            INSERT INTO attendance
            (
                roll_no,
                subject,
                date,
                time_marked,
                status
            )
            VALUES (?, ?, ?, ?, 'Present')
            """,
            (
                roll_no,
                subject,
                today,
                current_time
            )
        )

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": f"Roll No {roll_no} marked Present!"
    }), 200


# ============================================================
# STUDENT MARK ATTENDANCE
# ============================================================

@app.route(
    "/api/student/mark-attendance",
    methods=["POST", "OPTIONS"]
)
def mark_attendance():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:

        data = request.get_json() or {}

        roll_no = str(
            data.get("roll_no", "")
        ).strip()

        scanned_token = str(
            data.get("token", "")
        ).strip().upper()

        scanned_token = (
            scanned_token
            .replace(" ", "")
            .replace("\n", "")
        )

        # NEW: Factor 2 (dynamic code) + Factor 3 (geo-fencing) inputs
        entered_code = str(data.get("code", "")).strip()

        try:
            student_latitude = float(data.get("latitude"))
            student_longitude = float(data.get("longitude"))
        except (TypeError, ValueError):
            student_latitude = None
            student_longitude = None

        if not roll_no:

            return jsonify({
                "status": "error",
                "message": "Student Roll Number missing!"
            }), 400

        conn = get_db_connection()

        # ----------------------------------------------------
        # Find latest active session
        # ----------------------------------------------------

        session = conn.execute(
            """
            SELECT *
            FROM attendance_sessions
            WHERE status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        if not session:

            conn.close()

            return jsonify({
                "status": "error",
                "message": "No active session found! Please ask your teacher to start the session."
            }), 403

        # ----------------------------------------------------
        # Check expiry
        # ----------------------------------------------------

        try:
            expiry_time = datetime.fromisoformat(
                session["expiry_time"]
            )
        except Exception:

            conn.close()

            return jsonify({
                "status": "error",
                "message": "Session time invalid!"
            }), 500

        if datetime.now() > expiry_time:

            conn.execute(
                """
                UPDATE attendance_sessions
                SET status = 'expired'
                WHERE id = ?
                """,
                (session["id"],)
            )

            conn.commit()
            conn.close()

            return jsonify({
                "status": "error",
                "message": "The attendance session has expired!"
            }), 403

        # ----------------------------------------------------
        # QR VALIDATION (room-type aware — Class QR is valid only
        # for class sessions, Lab QR is valid only for lab sessions)
        # ----------------------------------------------------

        session_room_type = (session["room_type"] or "class").lower()

        if session_room_type == "lab":
            expected_tokens = LAB_QR_TOKENS
            expected_label = "Lab"
        else:
            expected_tokens = CLASS_QR_TOKENS
            expected_label = "Class"

        normalized_valid_tokens = [
            token.upper().replace(" ", "")
            for token in expected_tokens
        ]

        if scanned_token not in normalized_valid_tokens:

            conn.close()

            print(
                "QR mismatch!",
                scanned_token,
                normalized_valid_tokens
            )

            return jsonify({
                "status": "error",
                "message": f"Incorrect QR Code! This session is for '{expected_label}' — please scan the official {expected_label} QR code."
            }), 400

        # ----------------------------------------------------
        # FACTOR 2: DYNAMIC CODE VALIDATION
        # ----------------------------------------------------

        if not entered_code:

            conn.close()

            return jsonify({
                "status": "error",
                "message": "Please enter the 4-digit code shown on the blackboard!"
            }), 400

        session_code = (session["dynamic_code"] or "").strip()

        if entered_code != session_code:

            conn.close()

            return jsonify({
                "status": "error",
                "message": "Incorrect code! Please check the code written on the blackboard and try again."
            }), 400

        # Code has its own shorter expiry than the overall session
        code_expiry_raw = session["code_expiry"]

        if code_expiry_raw:

            try:
                code_expiry_time = datetime.fromisoformat(code_expiry_raw)
            except Exception:
                code_expiry_time = None

            if code_expiry_time and datetime.now() > code_expiry_time:

                conn.close()

                return jsonify({
                    "status": "error",
                    "message": "This code has expired! Please ask your teacher for a new code."
                }), 403

        # ----------------------------------------------------
        # FACTOR 3: GEO-FENCING VALIDATION
        # ----------------------------------------------------

        session_lat = session["latitude"]
        session_lng = session["longitude"]
        session_radius = session["radius_meters"] or DEFAULT_RADIUS_METERS

        # Geo-fencing is only checked when the teacher shared their
        # location while starting the session. If the teacher's
        # location wasn't saved (permission was denied), this check
        # is silently skipped — so the whole system isn't blocked
        # because of one missing permission.
        if session_lat is not None and session_lng is not None:

            if student_latitude is None or student_longitude is None:

                conn.close()

                return jsonify({
                    "status": "error",
                    "message": "Location access is required to mark attendance. Please allow location permission in your browser."
                }), 400

            distance = distance_in_meters(
                student_latitude, student_longitude,
                session_lat, session_lng
            )

            allowed_distance = session_radius + GEO_BUFFER_METERS

            if distance > allowed_distance:

                conn.close()

                print(
                    f"GEO-FENCE FAIL: roll_no={roll_no}, "
                    f"distance={distance:.1f}m, allowed={allowed_distance:.1f}m"
                )

                return jsonify({
                    "status": "error",
                    "message": "You are outside the classroom range! Attendance can only be marked from inside the classroom."
                }), 403

        # ----------------------------------------------------
        # STUDENT CHECK
        # ----------------------------------------------------

        student = conn.execute(
            """
            SELECT *
            FROM students
            WHERE roll_no = ?
            """,
            (roll_no,)
        ).fetchone()

        if not student:

            conn.close()

            return jsonify({
                "status": "error",
                "message": "Student record not found!"
            }), 404

        # ----------------------------------------------------
        # DUPLICATE CHECK
        # ----------------------------------------------------

        already_marked = conn.execute(
            """
            SELECT *
            FROM attendance
            WHERE roll_no = ?
            AND session_id = ?
            """,
            (
                roll_no,
                session["id"]
            )
        ).fetchone()

        if already_marked:

            conn.close()

            return jsonify({
                "status": "error",
                "message": "Attendance for this session has already been marked!"
            }), 409

        # ----------------------------------------------------
        # MARK ATTENDANCE
        # ----------------------------------------------------

        timestamp_date = datetime.now().strftime(
            "%Y-%m-%d"
        )

        timestamp_time = datetime.now().strftime(
            "%I:%M:%S %p"
        )

        conn.execute(
            """
            INSERT INTO attendance
            (
                roll_no,
                subject,
                date,
                time_marked,
                status,
                session_id
            )
            VALUES (?, ?, ?, ?, 'Present', ?)
            """,
            (
                roll_no,
                session["subject"],
                timestamp_date,
                timestamp_time,
                session["id"]
            )
        )

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Attendance Marked Successfully!",
            "roll_no": roll_no,
            "name": student["name"],
            "time": timestamp_time,
            "subject": session["subject"]
        }), 200

    except Exception as e:

        print("Server Error:", e)

        return jsonify({
            "status": "error",
            "message": "Server Error!"
        }), 500


# ============================================================
# INCHARGE - GET SUBJECT LIST
# ============================================================

@app.route(
    "/api/incharge/subjects",
    methods=["GET", "OPTIONS"]
)
def incharge_subjects():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT subject
        FROM teachers
        WHERE subject IS NOT NULL
        AND TRIM(subject) != ''

        UNION

        SELECT subject
        FROM attendance_sessions
        WHERE subject IS NOT NULL
        AND TRIM(subject) != ''

        UNION

        SELECT subject
        FROM attendance
        WHERE subject IS NOT NULL
        AND TRIM(subject) != ''

        ORDER BY subject ASC
        """
    ).fetchall()

    conn.close()

    subjects = [
        row["subject"]
        for row in rows
    ]

    return jsonify({
        "status": "success",
        "subjects": subjects
    }), 200


# ============================================================
# INCHARGE - CLASS DATA
#
# Filters:
# ?date=YYYY-MM-DD
# ?subject=Python
# ?roll_no=1001
# ?status=Present
# ============================================================

@app.route(
    "/api/incharge/class-data",
    methods=["GET", "OPTIONS"]
)
def incharge_class_data():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    date_filter = request.args.get(
        "date",
        ""
    ).strip()

    subject_filter = request.args.get(
        "subject",
        ""
    ).strip()

    roll_filter = request.args.get(
        "roll_no",
        ""
    ).strip()

    status_filter = request.args.get(
        "status",
        ""
    ).strip()

    conn = get_db_connection()

    # --------------------------------------------------------
    # RAW ATTENDANCE RECORDS
    # --------------------------------------------------------

    query = """
        SELECT
            a.id,
            a.roll_no,
            s.name,
            a.subject,
            a.date,
            a.time_marked,
            a.status,
            a.session_id,
            ats.teacher_name,
            ats.lecture
        FROM attendance a

        LEFT JOIN students s
            ON s.roll_no = a.roll_no

        LEFT JOIN attendance_sessions ats
            ON ats.id = a.session_id

        WHERE 1 = 1
    """

    params = []

    if date_filter:
        query += " AND a.date = ?"
        params.append(date_filter)

    if subject_filter:
        query += " AND a.subject = ?"
        params.append(subject_filter)

    if roll_filter:
        query += " AND a.roll_no = ?"
        params.append(roll_filter)

    if status_filter:
        query += " AND a.status = ?"
        params.append(status_filter)

    query += """
        ORDER BY
            a.date DESC,
            a.subject ASC,
            a.roll_no ASC
    """

    records = conn.execute(
        query,
        params
    ).fetchall()

    # --------------------------------------------------------
    # STUDENT LIST
    # --------------------------------------------------------

    students = conn.execute(
        """
        SELECT
            roll_no,
            name
        FROM students
        ORDER BY roll_no ASC
        """
    ).fetchall()

    # --------------------------------------------------------
    # SESSION DATA
    # --------------------------------------------------------

    session_query = """
        SELECT
            id,
            teacher_name,
            subject,
            lecture,
            start_time,
            expiry_time,
            status
        FROM attendance_sessions
        WHERE 1 = 1
    """

    session_params = []

    if date_filter:

        session_query += """
            AND DATE(start_time) = ?
        """

        session_params.append(date_filter)

    if subject_filter:

        session_query += """
            AND subject = ?
        """

        session_params.append(subject_filter)

    session_query += """
        ORDER BY start_time DESC
    """

    sessions = conn.execute(
        session_query,
        session_params
    ).fetchall()

    # --------------------------------------------------------
    # SUBJECT LIST (needed by incharge_dashboard.html's single
    # fetch — it reads result.subjects directly instead of
    # calling the separate /api/incharge/subjects endpoint)
    # --------------------------------------------------------

    subject_rows = conn.execute(
        """
        SELECT subject
        FROM teachers
        WHERE subject IS NOT NULL
        AND TRIM(subject) != ''

        UNION

        SELECT subject
        FROM attendance_sessions
        WHERE subject IS NOT NULL
        AND TRIM(subject) != ''

        UNION

        SELECT subject
        FROM attendance
        WHERE subject IS NOT NULL
        AND TRIM(subject) != ''

        ORDER BY subject ASC
        """
    ).fetchall()

    subject_list = [
        row["subject"]
        for row in subject_rows
    ]

    conn.close()

    return jsonify({
        "status": "success",

        "filters": {
            "date": date_filter,
            "subject": subject_filter,
            "roll_no": roll_filter,
            "status": status_filter
        },

        "students": [
            dict(row)
            for row in students
        ],

        "records": [
            dict(row)
            for row in records
        ],

        # "data" is an alias of "records" — incharge_dashboard.html's
        # frontend code reads result.data, so this key is required
        # for the dashboard table to actually populate.
        "data": [
            dict(row)
            for row in records
        ],

        "subjects": subject_list,

        "sessions": [
            dict(row)
            for row in sessions
        ],

        "total_records": len(records)
    }), 200


# ============================================================
# INCHARGE - INDIVIDUAL STUDENT DATA
# ============================================================

@app.route(
    "/api/incharge/student/<roll_no>",
    methods=["GET", "OPTIONS"]
)
def incharge_student_detail(roll_no):

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    roll_no = str(roll_no).strip()

    conn = get_db_connection()

    student = conn.execute(
        """
        SELECT
            roll_no,
            name
        FROM students
        WHERE roll_no = ?
        """,
        (roll_no,)
    ).fetchone()

    if not student:

        conn.close()

        return jsonify({
            "status": "error",
            "message": "Student not found!"
        }), 404

    # --------------------------------------------------------
    # STUDENT ATTENDANCE HISTORY
    # --------------------------------------------------------

    history = conn.execute(
        """
        SELECT
            a.id,
            a.roll_no,
            a.subject,
            a.date,
            a.time_marked,
            a.status,
            a.session_id,
            ats.teacher_name,
            ats.lecture
        FROM attendance a

        LEFT JOIN attendance_sessions ats
            ON ats.id = a.session_id

        WHERE a.roll_no = ?

        ORDER BY
            a.date DESC,
            a.id DESC
        """,
        (roll_no,)
    ).fetchall()

    # --------------------------------------------------------
    # SUBJECT-WISE SUMMARY
    # --------------------------------------------------------

    summary = conn.execute(
        """
        SELECT
            subject,
            COUNT(*) AS attendance_count
        FROM attendance
        WHERE roll_no = ?
        GROUP BY subject
        ORDER BY subject ASC
        """,
        (roll_no,)
    ).fetchall()

    conn.close()

    return jsonify({
        "status": "success",

        "student": dict(student),

        "history": [
            dict(row)
            for row in history
        ],

        "subject_summary": [
            dict(row)
            for row in summary
        ]
    }), 200


# ============================================================
# INCHARGE - STUDENT LIST WITH LATEST ATTENDANCE
# ============================================================

@app.route(
    "/api/incharge/students",
    methods=["GET", "OPTIONS"]
)
def incharge_students():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    date_filter = request.args.get(
        "date",
        ""
    ).strip()

    subject_filter = request.args.get(
        "subject",
        ""
    ).strip()

    conn = get_db_connection()

    query = """
        SELECT
            s.roll_no,
            s.name,
            a.subject,
            a.date,
            a.time_marked,
            a.status
        FROM students s

        LEFT JOIN attendance a
            ON s.roll_no = a.roll_no
    """

    conditions = []
    params = []

    if date_filter:

        conditions.append(
            "a.date = ?"
        )

        params.append(date_filter)

    if subject_filter:

        conditions.append(
            "a.subject = ?"
        )

        params.append(subject_filter)

    if conditions:

        query += " WHERE "
        query += " AND ".join(conditions)

    query += """
        ORDER BY
            s.roll_no ASC,
            a.date DESC
    """

    rows = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return jsonify({
        "status": "success",
        "data": [
            dict(row)
            for row in rows
        ]
    }), 200


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "success",
        "message": "Attendance Management System Backend is running!"
    }), 200


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        debug=True,
        port=5000
    )