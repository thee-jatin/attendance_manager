import sqlite3

conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# ---- Yahan us teacher ka username daalo jise delete karna hai ----
username = 'sharma01'
# -------------------------------------------------------------------

cursor.execute('DELETE FROM teachers WHERE username = ?', (username,))
conn.commit()

if cursor.rowcount > 0:
  print(f'Teacher "{username}" deleted successfully!')
else:
  print(f'No teacher found with username "{username}".')

conn.close()