from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    date = db.Column(db.Date)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(255), unique=True)
    last_name = db.Column(db.String(255))
    first_name = db.Column(db.String(255))
    middle_i = db.Column(db.String(10))
    course = db.Column(db.String(255))
    year = db.Column(db.String(10))

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    student_id = db.Column(db.String(255), db.ForeignKey('students.student_id'), nullable=True)
    first_name = db.Column(db.String(255), nullable=True)
    middle_i = db.Column(db.String(10), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)