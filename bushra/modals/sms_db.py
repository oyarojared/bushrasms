from datetime import datetime

from . import db


class SmsSettings(db.Model):
    __tablename__ = "sms_settings"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(
        db.Integer,
        db.ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    sender_name = db.Column(db.String(11), nullable=True)
    allow_class_teachers = db.Column(db.Boolean, default=True, nullable=False)
    credits = db.Column(db.Integer, default=0, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    branch = db.relationship("Branch")


class SmsTemplate(db.Model):
    __tablename__ = "sms_templates"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(
        db.Integer,
        db.ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(80), nullable=False)
    purpose = db.Column(db.String(30), nullable=False)
    body = db.Column(db.Text, nullable=False)
    for_teachers = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SmsMessage(db.Model):
    __tablename__ = "sms_messages"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(
        db.Integer,
        db.ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    purpose = db.Column(db.String(30), nullable=False)
    audience_type = db.Column(db.String(30), nullable=False)
    audience_label = db.Column(db.String(180), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("branch_classes.id"), nullable=True)
    stream = db.Column(db.String(50), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="queued")
    provider = db.Column(db.String(30), nullable=True)
    credits_used = db.Column(db.Integer, default=0, nullable=False)
    ready_count = db.Column(db.Integer, default=0, nullable=False)
    skipped_count = db.Column(db.Integer, default=0, nullable=False)
    sent_count = db.Column(db.Integer, default=0, nullable=False)
    failed_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    sender = db.relationship("Teacher")
    recipients = db.relationship(
        "SmsRecipient",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="SmsRecipient.id",
    )


class SmsRecipient(db.Model):
    __tablename__ = "sms_recipients"

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(
        db.Integer,
        db.ForeignKey("sms_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_type = db.Column(db.String(20), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=True)
    display_name = db.Column(db.String(150), nullable=False)
    detail = db.Column(db.String(180), nullable=True)
    phone_raw = db.Column(db.String(30), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False)
    skip_reason = db.Column(db.String(80), nullable=True)
    body = db.Column(db.Text, nullable=True)
    parts = db.Column(db.Integer, default=0, nullable=False)
    error = db.Column(db.String(250), nullable=True)

    message = db.relationship("SmsMessage", back_populates="recipients")
