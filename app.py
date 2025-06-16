from flask import Flask, render_template, request, redirect, jsonify, flash, session, url_for, Response
from datetime import date
from models import db, Event, Student, Attendance
import csv
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, LOGIN_PIN
from sqlalchemy import text
from models import db, Event, Student, Attendance
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = '81a6u3xft47odubrf431sqcg2wfeqnlbfh0nh1yucg'
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if logged in
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        # Check for inactivity (10 minutes = 600 seconds)
        last_active = session.get('last_active')
        now = time.time()
        if last_active and now - last_active > 600:
            session.clear()
            return redirect(url_for('login'))
        # Update last active time
        session['last_active'] = now
        return f(*args, **kwargs)
    return decorated_function

from flask import render_template

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin == LOGIN_PIN:
            session['logged_in'] = True
            session['last_active'] = time.time()
            return redirect(url_for('index'))
        else:
            error = "Invalid PIN"
    return render_template('auth.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
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
@login_required
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
@login_required
def create_event():
    name = request.form['event_name']
    date_str = request.form['event_date']
    event = Event(name=name, date=date_str)
    db.session.add(event)
    db.session.commit()
    return redirect('/')

@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    Attendance.query.filter_by(event_id=event_id).delete()
    Event.query.filter_by(id=event_id).delete()
    db.session.commit()
    return redirect('/')

@app.route('/edit_event/<int:event_id>', methods=['POST'])
@login_required
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
    # Only delete students, not attendance
    Student.query.delete()
    db.session.execute(text('ALTER TABLE students AUTO_INCREMENT = 1'))
    with open(csv_file, newline='', encoding='latin-1') as file:
        reader = csv.DictReader(file)
        for row in reader:
            student_id = row['student_id'].strip() or None
            student = Student(
                student_id=student_id,
                first_name=row['first_name'],
                last_name=row['last_name'],
                middle_i=row['middle_i'],
                course=row['course'],
                year=row['year']
            )
            db.session.add(student)
    db.session.commit()

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_students_csv():
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['csv_file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filepath = 'uploaded_students.csv'
            file.save(filepath)
            import_students_from_csv(filepath)
            flash('Students imported successfully!')
            return redirect('/upload')
    return render_template('upload.html')

@app.route('/download')
@login_required
def download():
    event_id = request.args.get('event_id')
    if not event_id:
        # Show event selection page
        events = Event.query.order_by(Event.date.desc()).all()
        return render_template('download.html', events=events)
    if not event_id.isdigit():
        return "Invalid event ID", 400

    event = Event.query.get(int(event_id))
    if not event:
        return "Event not found", 404

    records = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.student_id)
        .filter(Attendance.event_id == event_id)
        .all()
    )

    def generate():
        yield 'Student ID,Last Name,First Name,Middle Initial,Course,Year\n'
        for attendance, student in records:
            yield f'{student.student_id},{student.last_name},{student.first_name},{student.middle_i},{student.course},{student.year}\n'

    filename = f"Attendance {event.name}.csv"
    return Response(
        generate(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# Uncomment to import students on startup
# with app.app_context():
#     db.create_all()

if __name__ == '__main__':
    app.run(debug=False)