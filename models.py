import sqlite3

conn = sqlite3.connect('attendance.db')
c = conn.cursor()

# Create students table
c.execute('''
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    middle_i TEXT,
    course TEXT,
    year TEXT
)
''')

# Create events table
c.execute('''
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date TEXT NOT NULL
)
''')

# Create attendance table
c.execute('''
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    student_id TEXT,
    first_name TEXT,
    middle_i TEXT,
    last_name TEXT,
    FOREIGN KEY(event_id) REFERENCES events(id)
)
''')

conn.commit()
conn.close()

print("Database upgraded for events.")
