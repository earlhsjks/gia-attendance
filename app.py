from flask import Flask, render_template, request, redirect, jsonify
import mysql.connector
import csv
from waitress import serve
from datetime import date
import os
from config import MYSQL_CONFIG

app = Flask(__name__)

def get_db():
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    return conn

@app.route('/')
def index():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM events ORDER BY date DESC")
    events = cur.fetchall()
    event_id = request.args.get('event_id')
    selected_event = None
    students = []
    present_ids = set()
    present_names = []
    today = date.today().isoformat()

    if event_id:
        cur.execute("SELECT * FROM events WHERE id = %s", (event_id,))
        selected_event = cur.fetchone()
        cur.execute("SELECT * FROM students")
        students = cur.fetchall()
        cur.execute("SELECT student_id FROM attendance WHERE event_id = %s", (event_id,))
        present = cur.fetchall()
        present_ids = set([row['student_id'] for row in present if row['student_id']])
        cur.execute(
            "SELECT first_name, middle_i, last_name FROM attendance WHERE event_id = %s AND (student_id IS NULL OR student_id = '' OR student_id = 'None')",
            (event_id,)
        )
        present_names = cur.fetchall()
    cur.close()
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
    ajax = request.form.get('ajax')
    conn = get_db()

    student = None
    cur = conn.cursor(dictionary=True)
    if student_id and student_id.lower() != "none" and student_id.strip() != "":
        cur.execute(
            "INSERT IGNORE INTO attendance (event_id, student_id) VALUES (%s, %s)",
            (event_id, student_id)
        )
        cur.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cur.fetchone()
    else:
        full_name = request.form.get('student_search', '').strip()
        last_name, rest = full_name.split(',', 1) if ',' in full_name else (full_name, '')
        rest = rest.strip()
        parts = rest.split(' ')
        first_name = parts[0] if len(parts) > 0 else ''
        middle_i = parts[1].replace('.', '').strip() if len(parts) > 1 else ''
        cur.execute(
            "INSERT IGNORE INTO attendance (event_id, first_name, middle_i, last_name) VALUES (%s, %s, %s, %s)",
            (event_id, first_name.strip(), middle_i, last_name.strip())
        )
        student = {'first_name': first_name.strip(), 'middle_i': middle_i, 'last_name': last_name.strip(), 'student_id': None, 'course': '', 'year': ''}
    conn.commit()
    cur.close()
    conn.close()

    if ajax:
        if student:
            # If student is a Row object, convert to dict
            if not isinstance(student, dict):
                student = dict(student)
            return jsonify(success=True, student=student)
        else:
            return jsonify(success=False)
    else:
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
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM students')
    cur.execute('ALTER TABLE students AUTO_INCREMENT = 1')
    with open(csv_file, newline='', encoding='latin-1') as file:
        reader = csv.DictReader(file)
        for row in reader:
            student_id = row['student_id'].strip() or None
            cur.execute('''
                INSERT IGNORE INTO students 
                (student_id, last_name, first_name, middle_i, course, year)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                student_id,
                row['last_name'],
                row['first_name'],
                row['middle_i'],
                row['course'],
                row['year']
            ))
    conn.commit()
    cur.close()
    conn.close()

import_students_from_csv('students.csv')