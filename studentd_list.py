import sqlite3

conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

cursor.execute('SELECT roll_no, name FROM students ORDER BY roll_no')
rows = cursor.fetchall()

print(f'Total students: {len(rows)}\n')
for row in rows:
  print(f'Roll No: {row[0]} | Name: {row[1]}')

conn.close()





