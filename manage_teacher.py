import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# ---- Yahan teacher ki details edit karo ----
name = 'MR. VISHESH'
username = 'DSTL'
password = '204'
subject = 'DSTL'          # <-- YEH FIELD MISSING THI, ab add ki hai.
                             #     Yahi subject teacher ke dashboard par
                             #     "ASSIGNED SUBJECT" ki tarah dikhega,
                             #     aur isi se uski attendance table filter
                             #     hoti hai. Naya teacher add karte waqt
                             #     yeh field bharna ZARURI hai.
# --------------------------------------------

hashed_pw = generate_password_hash(password)

cursor.execute(
    """
    INSERT INTO teachers (name, username, password, subject)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(username) DO UPDATE SET
      name = excluded.name,
      password = excluded.password,
      subject = excluded.subject
    """,
    (name, username, hashed_pw, subject),
)

conn.commit()
conn.close()
print(f'Teacher "{username}" ({subject}) added/updated successfully!')