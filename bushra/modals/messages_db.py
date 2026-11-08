from datetime import datetime

from . import db


class StaffMessage(db.Model):
    """One notice sent to one or more staff accounts."""

    __tablename__ = "staff_messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id = db.Column(
        db.Integer,
        db.ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    channel = db.Column(db.String(20), nullable=False, default="in_app")
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    audience_label = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship("Teacher", foreign_keys=[sender_id])
    branch = db.relationship("Branch")
    recipients = db.relationship(
        "StaffMessageRecipient",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="StaffMessageRecipient.id",
    )


class StaffMessageRecipient(db.Model):
    """One staff member's copy of a notice, including when they opened it."""

    __tablename__ = "staff_message_recipients"

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(
        db.Integer,
        db.ForeignKey("staff_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opened_at = db.Column(db.DateTime, nullable=True)

    message = db.relationship("StaffMessage", back_populates="recipients")
    teacher = db.relationship("Teacher", foreign_keys=[teacher_id])

    __table_args__ = (
        db.UniqueConstraint(
            "message_id", "teacher_id", name="uq_staff_message_recipient"
        ),
    )
