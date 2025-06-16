from flask import Flask, render_template, request, redirect, jsonify
from datetime import date
from models import db, Event, Student, Attendance
import csv
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from sqlalchemy import text
from models import db, Event, Student, Attendance

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
db.init_app(app)

@app.route('/')
def index():
    events = Event.query.order_by(Event.date.desc()).all()
    event_id = request.args.get('event_id')
    selected_event = None
    students = []
    present_ids = set()
    present_names = []
    today = date.today().isoformat()

    if event_id:
        selected_event = Event.query.get(event_id)
        students = Student.query.all()
        present = Attendance.query.filter_by(event_id=event_id).filter(Attendance.student_id.isnot(None)).all()
        present_ids = set([a.student_id for a in present if a.student_id])
        present_names = Attendance.query.filter_by(event_id=event_id).filter(
            (Attendance.student_id == None) | (Attendance.student_id == '') | (Attendance.student_id == 'None')
        ).with_entities(Attendance.first_name, Attendance.middle_i, Attendance.last_name).all()

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
    student = None

    # Ensure event_id is valid and exists
    if not event_id or not event_id.isdigit() or not Event.query.get(int(event_id)):
        if ajax:
            return jsonify(success=False, error="Invalid event_id"), 400
        else:
            return redirect('/')

    event_id = int(event_id)

    if student_id and student_id.lower() != "none" and student_id.strip() != "":
        exists = Attendance.query.filter_by(event_id=event_id, student_id=student_id).first()
        if not exists:
            attendance = Attendance(event_id=event_id, student_id=student_id)
            db.session.add(attendance)
            db.session.commit()
        student = Student.query.filter_by(student_id=student_id).first()
    else:
        full_name = request.form.get('student_search', '')
        if not full_name or not isinstance(full_name, str):
            if ajax:
                return jsonify(success=False, error="No student name provided"), 400
            else:
                return redirect(f"/?event_id={event_id}")
        full_name = full_name.strip()
        last_name, rest = full_name.split(',', 1) if ',' in full_name else (full_name, '')
        rest = rest.strip()
        parts = rest.split(' ')
        first_name = parts[0] if len(parts) > 0 else ''
        middle_i = parts[1].replace('.', '').strip() if len(parts) > 1 else ''
        attendance = Attendance(
            event_id=event_id,
            first_name=first_name.strip(),
            middle_i=middle_i,
            last_name=last_name.strip()
        )
        db.session.add(attendance)
        db.session.commit()
        student = {'first_name': first_name.strip(), 'middle_i': middle_i, 'last_name': last_name.strip(), 'student_id': None, 'course': '', 'year': ''}

    if ajax:
        if student:
            if not isinstance(student, dict):
                student = {
                    'first_name': getattr(student, 'first_name', ''),
                    'middle_i': getattr(student, 'middle_i', ''),
                    'last_name': getattr(student, 'last_name', ''),
                    'student_id': getattr(student, 'student_id', None),
                    'course': getattr(student, 'course', ''),
                    'year': getattr(student, 'year', '')
                }
            return jsonify(success=True, student=student)
        else:
            return jsonify(success=False)
    else:
        return redirect(f"/?event_id={event_id}")

@app.route('/create_event', methods=['POST'])
def create_event():
    name = request.form['event_name']
    date_str = request.form['event_date']
    event = Event(name=name, date=date_str)
    db.session.add(event)
    db.session.commit()
    return redirect('/')

@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    Attendance.query.filter_by(event_id=event_id).delete()
    Event.query.filter_by(id=event_id).delete()
    db.session.commit()
    return redirect('/')

@app.route('/edit_event/<int:event_id>', methods=['POST'])
def edit_event(event_id):
    name = request.form['event_name']
    date_str = request.form['event_date']
    event = Event.query.get(event_id)
    if event:
        event.name = name
        event.date = date_str
        db.session.commit()
    return redirect(f"/?event_id={event_id}")

def import_students_from_csv(csv_file):
    Student.query.delete()
    db.session.execute(text('ALTER TABLE students AUTO_INCREMENT = 1'))
    with open(csv_file, newline='', encoding='latin-1') as file:
        reader = csv.DictReader(file)
        for row in reader:
            student_id = row['student_id'].strip() or None
            student = Student(
                student_id=student_id,
                last_name=row['last_name'],
                first_name=row['first_name'],
                middle_i=row['middle_i'],
                course=row['course'],
                year=row['year']
            )
            db.session.add(student)
    db.session.commit()

# Uncomment to import students on startup
with app.app_context():
    # db.create_all()
    import_students_from_csv('students.csv')