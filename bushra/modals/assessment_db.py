from datetime import datetime
from sqlalchemy.dialects.mysql import JSON
from . import db


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.Enum("I", "II", "III", name="exam_terms"), nullable=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    is_inactive = db.Column(db.Boolean, default=False, nullable=False)

    exam_branches = db.relationship(
        "ExamBranch",
        back_populates="exam",
        cascade="all, delete-orphan"
    )


class ExamBranch(db.Model):
    __tablename__ = "exam_branches"

    id = db.Column(db.Integer, primary_key=True)

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False
    )

    branch_id = db.Column(
        db.Integer,
        db.ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False
    )

    exam = db.relationship("Exam", back_populates="exam_branches")
    branch = db.relationship("Branch", back_populates="exam_branches")

    __table_args__ = (
        db.UniqueConstraint("exam_id", "branch_id", name="uq_exam_branch"),
    )

 
 

class ExamPaper(db.Model):
    __tablename__ = "exam_papers"

    id = db.Column(db.Integer, primary_key=True)

    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("branch_classes.id"), nullable=False)

    stream = db.Column(db.String(50), nullable=True)

    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)

    marks_out_of = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ REQUIRED RELATIONSHIPS
    exam = db.relationship("Exam", backref=db.backref("exam_papers", lazy="dynamic"))
    subject = db.relationship("Subject")
    branch_class = db.relationship("BranchClasses")

    __table_args__ = (
        db.UniqueConstraint(
            "exam_id",
            "branch_id",
            "class_id",
            "stream",
            "subject_id",
            name="uq_exam_paper"
        ),
    )


class StudentExamMark(db.Model):
    __tablename__ = "student_exam_marks"

    id = db.Column(db.Integer, primary_key=True)

    exam_paper_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_papers.id", ondelete="CASCADE"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False
    )

    marks = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "exam_paper_id",
            "student_id",
            name="uq_student_exam_mark"
        ),
    )



# =========================
# 1️⃣ Grading System
# =========================
class GradingSystem(db.Model):
    __tablename__ = "grading_systems"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)  # CBC or 8-4-4
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship: one system -> many schemes
    schemes = db.relationship("GradingScheme", backref="system", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GradingSystem {self.name}>"


# =========================
# 2️⃣ Grading Scheme
# =========================
class GradingScheme(db.Model):
    __tablename__ = "grading_schemes"

    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.Integer, db.ForeignKey("grading_systems.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(50), nullable=True)  # e.g., "2026 CBC Scheme"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship: one scheme -> many boundaries
    boundaries = db.relationship("GradingBoundary", backref="scheme", cascade="all, delete-orphan")

    # Relationship: grades that use this scheme
    grades = db.relationship("GradeGradingScheme", backref="scheme", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GradingScheme {self.name or self.id} ({self.system.name})>"


# =========================
# 3️⃣ Grading Boundaries
# =========================
class GradingBoundary(db.Model):
    __tablename__ = "grading_boundaries"

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(db.Integer, db.ForeignKey("grading_schemes.id", ondelete="CASCADE"), nullable=False)
    
    min_score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    performance_level = db.Column(db.String(20), nullable=False)  # EE1, A, B, etc.
    points = db.Column(db.Integer, nullable=True)
    descriptor = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    def __repr__(self):
        return f"<Boundary {self.performance_level}: {self.min_score}-{self.max_score}>"


# =========================
# 4️⃣ Grade ↔ Grading Scheme
# =========================
class GradeGradingScheme(db.Model):
    __tablename__ = "grade_grading_schemes"

    id = db.Column(db.Integer, primary_key=True)
    grade_id = db.Column(db.Integer, db.ForeignKey("branch_classes.id", ondelete="CASCADE"), nullable=False)
    scheme_id = db.Column(db.Integer, db.ForeignKey("grading_schemes.id", ondelete="CASCADE"), nullable=False)

    # Relationships backrefs
    grade = db.relationship("BranchClasses", backref="grading_schemes")

    def __repr__(self):
        return f"<GradeGradingScheme Grade {self.grade.grade_form} -> Scheme {self.scheme.name}>"
