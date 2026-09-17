import sqlite3

conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# ---- Yahan us student ka roll_no daalo jise delete karna hai ----
roll_no = '2108'
# --------------------------------------------------------------------

cursor.execute('DELETE FROM students WHERE roll_no = ?', (roll_no,))
conn.commit()

if cursor.rowcount > 0:
  print(f'Student "{roll_no}" deleted successfully!')
else:
  print(f'No student found with roll_no "{roll_no}".')

conn.close()