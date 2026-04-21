from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

from . import db


class Teacher(db.Model, UserMixin):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)

    # Foreign key to branches table
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)

    # Teacher details
    employer = db.Column(db.String(10), nullable=False)  # 'TSC' or 'BOM'
    fullname = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(1), nullable=False)  # 'M' or 'F', optional
    staff_id = db.Column(db.String(30), nullable=True)  # optional
    title = db.Column(db.String(10), nullable=False)  # Mr., Mrs., etc.
    id_no = db.Column(db.Integer, nullable=True)  # optional
    tsc_no = db.Column(db.String(20), unique=True, nullable=True)  # optional
    phone = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # optional
    username = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(250), nullable=False)
    passport_url = db.Column(db.String(250))
    is_admin = db.Column(db.Boolean, default=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now()
    )

    # Relationship
    branch = db.relationship("Branch", backref=db.backref("teachers", lazy=True))
    lessons = db.relationship(
        "Lesson",
        backref="teacher",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    @property
    def allocations(self):
        return [
            { 
                "subject_id": lesson.subject.id,
                "subject_name": lesson.subject.name,
                "class_id": lesson.class_.id,
                "class_name": lesson.class_.grade_form,
                "stream": lesson.stream
            }
            for lesson in self.lessons
        ]


    def __repr__(self):
        return f"<Teacher {self.fullname} ({self.branch_id})>"


class ClassTeacher(db.Model):
    __tablename__ = "class_teachers"

    id = db.Column(db.Integer, primary_key=True)

    branch_id = db.Column(
        db.Integer,
        db.ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False
    )
    class_id = db.Column(
        db.Integer,
        db.ForeignKey("branch_classes.id", ondelete="CASCADE"),
        nullable=False
    )
    stream = db.Column(db.String(20), nullable=True)  # nullable for classes without streams
    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now()
    )

    # Relationships
    branch = db.relationship("Branch", backref=db.backref("class_teachers", lazy=True, passive_deletes=True))
    class_ = db.relationship("BranchClasses", backref=db.backref("class_teachers", lazy=True, passive_deletes=True))
    teacher = db.relationship("Teacher", backref=db.backref("class_teacher_assignments", lazy=True, passive_deletes=True))

    def __repr__(self):
        return f"<ClassTeacher Branch:{self.branch_id} Class:{self.class_id} Stream:{self.stream} Teacher:{self.teacher_id}>"
