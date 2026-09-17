import sqlite3

conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

cursor.execute('SELECT id, name, username FROM teachers ORDER BY id')
rows = cursor.fetchall()

print(f'Total teachers: {len(rows)}\n')
for row in rows:
  print(f'ID: {row[0]} | Name: {row[1]} | Username: {row[2]}')

conn.close()