from flask import Flask, render_template, request, redirect
import sqlite3, csv
from waitress import serve
from datetime import date

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db()
    events = conn.execute("SELECT * FROM events ORDER BY date DESC").fetchall()
    event_id = request.args.get('event_id')
    selected_event = None
    students = []
    present_ids = set()
    present_names = []
    today = date.today().isoformat()

    if event_id:
        selected_event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        students = conn.execute("SELECT * FROM students").fetchall()
        present = conn.execute("SELECT student_id FROM attendance WHERE event_id = ?", (event_id,)).fetchall()
        present_ids = set([row['student_id'] for row in present if row['student_id']])
        present_names = conn.execute(
            "SELECT first_name, middle_i, last_name FROM attendance WHERE event_id = ? AND (student_id IS NULL OR student_id = '' OR student_id = 'None')",
            (event_id,)
        ).fetchall()
    conn.close()
    return render_template(
        'index.html',
        events=events,
        selected_event=selected_event,
        students=students,
        present_ids=present_ids,
        present_names=present_names,
        today=today,
        event_id=event_id
    )

@app.route('/mark', methods=['POST'])
def mark():
    student_id = request.form['student_id']
    event_id = request.form['event_id']
    conn = get_db()

    if student_id and student_id.lower() != "none" and student_id.strip() != "":
        conn.execute(
            "INSERT OR IGNORE INTO attendance (event_id, student_id) VALUES (?, ?)",
            (event_id, student_id)
        )
    else:
        full_name = request.form.get('student_search', '').strip()
        last_name, rest = full_name.split(',', 1) if ',' in full_name else (full_name, '')
        rest = rest.strip()
        parts = rest.split(' ')
        first_name = parts[0] if len(parts) > 0 else ''
        middle_i = ''
        if len(parts) > 1:
            middle_i = parts[1].replace('.', '').strip()
        conn.execute(
            "INSERT OR IGNORE INTO attendance (event_id, first_name, middle_i, last_name) VALUES (?, ?, ?, ?)",
            (event_id, first_name.strip(), middle_i, last_name.strip())
        )

    conn.commit()
    conn.close()
    return redirect(f"/?event_id={event_id}")

@app.route('/create_event', methods=['POST'])
def create_event():
    name = request.form['event_name']
    date_str = request.form['event_date']
    conn = get_db()
    conn.execute("INSERT INTO events (name, date) VALUES (?, ?)", (name, date_str))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    conn = get_db()
    conn.execute("DELETE FROM attendance WHERE event_id = ?", (event_id,))
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/edit_event/<int:event_id>', methods=['POST'])
def edit_event(event_id):
    name = request.form['event_name']
    date_str = request.form['event_date']
    conn = get_db()
    conn.execute("UPDATE events SET name = ?, date = ? WHERE id = ?", (name, date_str, event_id))
    conn.commit()
    conn.close()
    return redirect(f"/?event_id={event_id}")

def import_students_from_csv(csv_file):
    conn = sqlite3.connect('attendance.db')
    cur = conn.cursor()

    # Delete all existing student records
    cur.execute('DELETE FROM students')
    # Reset the auto-increment counter for the students table
    cur.execute('DELETE FROM sqlite_sequence WHERE name="students"')

    # Use latin-1 encoding to handle special characters
    with open(csv_file, newline='', encoding='latin-1') as file:
        reader = csv.DictReader(file)
        for row in reader:
            student_id = row['student_id'].strip() or None  # Convert blank to None/NULL
            cur.execute('''
                INSERT OR IGNORE INTO students 
                (student_id, last_name, first_name, middle_i, course, year)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                student_id,
                row['first_name'],
                row['last_name'],
                row['middle_i'],
                row['course'],
                row['year']
            ))

    conn.commit()
    conn.close()

# Run Flask App
if __name__ == '__main__':
    import_students_from_csv('students.csv')
    # serve(app, host='0.0.0.0', port=5001)
    app.run(host='0.0.0.0', port=4001, debug=True)