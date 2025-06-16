from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    middle_i = db.Column(db.String(10))
    course = db.Column(db.String(100))
    year = db.Column(db.String(20))

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete="CASCADE"), nullable=False)
    student_id = db.Column(db.String(50), db.ForeignKey('students.student_id', ondelete="SET NULL"), nullable=True)
    first_name = db.Column(db.String(100))
    middle_i = db.Column(db.String(10))
    last_name = db.Column(db.String(100))