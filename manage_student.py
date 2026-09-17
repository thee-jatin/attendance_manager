import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# ---- Yahan student ki details edit karo ----
roll_no = '2103'
name = 'JATIN KUMAR'
password = '20202'
# ---------------------------------------------

hashed_pw = generate_password_hash(password)

cursor.execute(
    """
    INSERT INTO students (roll_no, name, password)
    VALUES (?, ?, ?)
    ON CONFLICT(roll_no) DO UPDATE SET
      name = excluded.name,
      password = excluded.password
    """,
    (roll_no, name, hashed_pw),
)

conn.commit()
conn.close()
print(f'Student "{roll_no}" ({name}) added/updated successfully!')