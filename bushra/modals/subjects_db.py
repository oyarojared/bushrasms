from datetime import datetime
from . import db
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True, index=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=False)
    is_examinable = db.Column(db.Boolean, default=False)
    is_compulsory = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    eligibility = db.relationship(
        "SubjectEligibility",
        backref="subject",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    student_allocations = db.relationship(
        "StudentSubjectAllocation",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


    def __repr__(self):
        return f"<Subject {self.name}>"


class SubjectEligibility(db.Model):
    __tablename__ = "subject_eligibility"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False
    )
    grade_form = db.Column(db.String(50), nullable=False)  # e.g., "Grade 10", "Form 2"

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("subject_id", "grade_form", name="uix_subject_grade"),
    )

    def __repr__(self):
        return f"<SubjectEligibility {self.subject_id} → {self.grade_form}>"


 
class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)

    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id",  ondelete="CASCADE"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("branch_classes.id"), nullable=False)
    stream = db.Column(db.String(50), nullable=True)

    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"),  nullable=False)
# 
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)

    subject = db.relationship("Subject")
    class_ = db.relationship("BranchClasses")

