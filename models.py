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
        db.String(50),
        nullable=False
    )

    qc_owner = db.Column(
        db.String(100)
    )

# =====================================================
# REPORT TABLE
# =====================================================

class Report(db.Model):
    qc_selected_tags = db.Column(db.Text)
    employee_name = db.Column(db.String(100))
    employee_timestamp = db.Column(db.String(100))
    qc_name = db.Column(db.String(100))
    qc_timestamp = db.Column(db.String(100))
    escalation_reason = db.Column(db.Text)



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

    bucket = db.Column(
        db.String(100)
    )

    assigned_to = db.Column(
        db.String(100)
    )

    status = db.Column(
        db.String(100),
        default="Pending"
    )

    selected_tags = db.Column(
        db.Text
    )

    qc_required = db.Column(
        db.Boolean,
        default=False
    )

    qc_assigned_to = db.Column(
        db.String(100)
    )

    mismatch = db.Column(
        db.Boolean,
        default=False
    )

    appeal_status = db.Column(
        db.String(50)
    )

# =====================================================
# GLOBAL TAXONOMY TABLE
# =====================================================

class GlobalTaxonomy(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    tags = db.Column(
        db.Text
    )