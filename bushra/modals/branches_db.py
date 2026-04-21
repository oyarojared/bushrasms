from datetime import datetime
from sqlalchemy.dialects.mysql import JSON
from . import db
from .staff_db import Teacher

class Branch(db.Model):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)

    branch_name = db.Column(db.String(150), nullable=False, unique=True, index=True)
    school_code = db.Column(db.String(8), nullable=False, unique=True, index=True)

    branch_manager = db.Column(db.String(100), nullable=False)
    branch_level = db.Column(db.String(20), nullable=False)
    branch_head = db.Column(db.String(100), nullable=True)

    school_gender = db.Column(db.String(20), nullable=False)
    school_type = db.Column(db.String(20), nullable=False)

    email = db.Column(db.String(120), nullable=True, unique=False)
    logo = db.Column(db.String(250), nullable=True)
    motto = db.Column(db.String(250), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 🔥 CASCADE DELETE RELATIONSHIP
    classes = db.relationship(
        "BranchClasses",
        backref="branch",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    exam_branches = db.relationship(
        "ExamBranch",
        back_populates="branch",
        cascade="all, delete-orphan"
    )
    def to_dict(self):
        return {
            "id": self.id,
            "branch_name": self.branch_name,
            "school_code": self.school_code,
            "branch_manager": self.branch_manager,
            "branch_level": self.branch_level,
            "branch_head": Teacher.query.get(self.branch_head).fullname if self.branch_head else None,
            "school_gender": self.school_gender,
            "school_type": self.school_type,
            "email": self.email,
            "logo": self.logo,
            "motto": self.motto,
    }
        
    def __repr__(self):
        return f"<Branch {self.branch_name}>"


class BranchClasses(db.Model):
    __tablename__ = "branch_classes"

    id = db.Column(db.Integer, primary_key=True)

    # 🔥 CASCADE ON DELETE in database level
    branch_id = db.Column(
        db.Integer,
        db.ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False
    )

    class_year = db.Column(db.String(4), nullable=False)
    grade_form = db.Column(db.String(50), nullable=False)
    streams = db.Column(JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
