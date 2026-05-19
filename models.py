from database import db

# =====================================================
# EMPLOYEE TABLE
# =====================================================

class Employee(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(100),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        default="employee"
    )

    qc_owner = db.Column(
        db.String(100)
    )

# =====================================================
# REPORT TABLE
# =====================================================

class Report(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    report_id = db.Column(
        db.String(100),
        unique=True
    )

    content = db.Column(
        db.Text
    )

    taxonomy = db.Column(
        db.Text
    )

    selected_tags = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )

    assigned_to = db.Column(
        db.String(100)
    )

    qc_assigned_to = db.Column(
        db.String(100)
    )

    qc_required = db.Column(
        db.Boolean,
        default=False
    )

    qc_tags = db.Column(
        db.Text
    )

    qc_status = db.Column(
        db.String(50),
        default="Pending"
    )

    mismatch = db.Column(
        db.Boolean,
        default=False
    )

    employee_comment = db.Column(
        db.Text
    )

    qa_comment = db.Column(
        db.Text
    )

    final_tag = db.Column(
        db.Text
    )

    appeal_status = db.Column(
        db.String(20),
        default="NO"
    )

    qa_status = db.Column(
        db.String(20),
        default="NO"
    )

    bucket = db.Column(
        db.String(100)
    )
    class GlobalTaxonomy(db.Model):

     id = db.Column(
        db.Integer,
        primary_key=True
    )

    tags = db.Column(
        db.Text
    )