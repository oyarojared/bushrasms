from datetime import date, datetime
from . import db
from ..modals.subjects_db import SubjectEligibility


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)

    # --- Foreign Keys ---
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("branch_classes.id"), nullable=False)

    # If class has streams
    stream = db.Column(db.String(50), nullable=True)

    # --- Student Personal Details ---
    admission_number = db.Column(db.Integer, nullable=False)
    fullname = db.Column(db.String(40), nullable=False)

    knec_assessment_no = db.Column(db.String(50), nullable=True)
    nemis_number = db.Column(db.String(50), nullable=True)
    birth_cert_no = db.Column(db.String(50), nullable=True)

    gender = db.Column(db.String(10), nullable=True)
    dob = db.Column(db.Date, nullable=True)

    boarding_status = db.Column(db.String(20), nullable=True)
    pathway = db.Column(db.String(30), nullable=True)

    # --- KCPE ---
    kcpe_marks = db.Column(db.Integer, nullable=True)
    kcpe_index_no = db.Column(db.String(50), nullable=True)
    kcpe_year = db.Column(db.Integer, nullable=True)

    # --- Admission ---
    date_of_admission = db.Column(db.Date, nullable=False, default=date.today)

    # --- Parent Details ---
    parent_fullname = db.Column(db.String(100), nullable=True)
    parent_phone = db.Column(db.String(15), nullable=True)

    passport = db.Column(db.String(200))

    # --- Relationships ---
    branch = db.relationship("Branch", backref="students")
    class_info = db.relationship("BranchClasses", backref="students")

    # Student OWNS subject allocations
    subject_allocations = db.relationship(
        "StudentSubjectAllocation",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    @property
    def subjects_taken(self):
        """
        Returns a list of subject names assigned to this student.
        """
        
        return [alloc.subject.name for alloc in self.subject_allocations if alloc.subject]

    # --- Composite Unique Constraint ---
    __table_args__ = (
        db.UniqueConstraint("branch_id", "admission_number", name="uq_branch_adm"),
    )
    

    def __repr__(self):
        return f"<Student {self.fullname}>"


class StudentSubjectAllocation(db.Model):
    __tablename__ = "student_subject_allocation"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False
    )

    allocated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Relationships (NO cascades here) ---
    student = db.relationship(
        "Student",
        back_populates="subject_allocations"
    )

    subject = db.relationship(
        "Subject",
        back_populates="student_allocations"
    )

    __table_args__ = (
        db.UniqueConstraint("student_id", "subject_id", name="uq_student_subject"),
    )

    def __repr__(self):
        return f"<Allocation Student:{self.student_id} Subject:{self.subject_id}>"
