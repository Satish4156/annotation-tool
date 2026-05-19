from flask import Flask, render_template, request, redirect, session
import random
from database import db
from models import (

    Employee,

    Report,

    GlobalTaxonomy
)
import os
import secrets
import pandas as pd

app = Flask(__name__)


app.secret_key = secrets.token_hex(16)

# =====================================================
# DATABASE CONFIG
# =====================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL is None:
    DATABASE_URL = "sqlite:///annotation.db"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


with app.app_context():

    db.create_all()

    admin_exists = Employee.query.filter_by(
        username="admin"
    ).first()

    if not admin_exists:

        admin = Employee(
            username="admin",
            password="admin123",
            role="admin"
        )

        db.session.add(admin)

        db.session.commit()

# =====================================================
# LOGIN
# =====================================================

@app.route('/', methods=['GET', 'POST'])

def login():

    if request.method == 'POST':
        common_tags = request.form.get(
    'common_tags'
)

        username = request.form.get(
            'username'
        ).strip()

        password = request.form.get(
            'password'
        ).strip()

        user = Employee.query.filter_by(
            username=username,
            password=password
        ).first()

        if user:

            session['username'] = user.username
            session['role'] = user.role

            if user.role == "admin":
                return redirect('/admin')

            elif user.role == "quality_reviewer":
                return redirect('/quality-reviewer')
            
            elif user.role == "team_lead":
                 return redirect('/team-lead')
            
            elif user.role == "quality_reviewer":
                 return redirect('/qc-dashboard')

            else:
                return redirect('/employee')

        else:
            return "Invalid Login"

    return render_template('login.html')

# =====================================================
# QC DASHBOARD
# =====================================================

@app.route('/qc-dashboard')

def qc_dashboard():



    reports = Report.query.filter(

        Report.status == "QC Pending"

    ).all()

    mismatch_reports = Report.query.filter_by(
        mismatch=True
    ).all()

    return render_template(

        'qc_dashboard.html',

        reports=reports,

        mismatch_reports=mismatch_reports
    )

# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route('/admin')
def admin():

    if 'username' not in session:
        return redirect('/')

    # ================================================
    # FILTERS
    # ================================================

    status_filter = request.args.get(
        'status',
        ''
    )

    search = request.args.get(
        'search',
        ''
    )

    # ================================================
    # REPORT QUERY
    # ================================================

    reports_query = Report.query

    if status_filter != '':

        reports_query = reports_query.filter_by(
            status=status_filter
        )

    if search != '':

        reports_query = reports_query.filter(
            Report.report_id.ilike(f"%{search}%")
        )

    reports = reports_query.all()

    # ================================================
    # COUNTS
    # ================================================

    total_reports = Report.query.count()

    pending_reports = Report.query.filter_by(
        status="Pending"
    ).count()

    completed_reports = Report.query.filter_by(
        status="Completed"
    ).count()

    escalated_reports = Report.query.filter_by(
        status="Escalated"
    ).count()

    mismatch_reports = Report.query.filter_by(
        mismatch=True
    ).count()

    qc_pending_reports = Report.query.filter_by(
        status="QC Pending"
    ).count()

    employees = Employee.query.all()

    # ================================================
    # EMPLOYEE STATS
    # ================================================

    employee_stats = []

    for employee in employees:

        completed_count = Report.query.filter_by(
            assigned_to=employee.username,
            status="Completed"
        ).count()

        progress_count = Report.query.filter_by(
            assigned_to=employee.username,
            status="In Progress"
        ).count()

        escalated_count = Report.query.filter_by(
            assigned_to=employee.username,
            status="Escalated"
        ).count()

        pending_count = Report.query.filter(
            Report.assigned_to == employee.username,
            Report.status.in_([
                "Pending",
                "In Progress"
            ])
        ).count()

        employee_stats.append({
            "username": employee.username,
            "role": employee.role,
            "completed": completed_count,
            "progress": progress_count,
            "pending": pending_count,
            "escalated": escalated_count
        })

    return render_template(
        'admin.html',
        total_reports=total_reports,
        pending_reports=pending_reports,
        completed_reports=completed_reports,
        escalated_reports=escalated_reports,
        mismatch_reports=mismatch_reports,
        qc_pending_reports=qc_pending_reports,
        employee_stats=employee_stats,
        reports=reports
    )



# =====================================================
# CREATE EMPLOYEE
# =====================================================

@app.route('/create_employee', methods=['POST'])

def create_employee():

    if 'username' not in session:
        return redirect('/')

    username = request.form.get(
        'username'
    ).strip()

    password = request.form.get(
        'password'
    ).strip()

    employee_exists = Employee.query.filter_by(
        username=username
    ).first()

    if employee_exists:
        return "Employee Already Exists"

    employee = Employee(

        username=username,

        password=password,

        role=request.form.get('role'),

        qc_owner=request.form.get('qc_owner')
    )

    db.session.add(employee)

    db.session.commit()

    return redirect('/admin')
# =====================================================
# UPLOAD REPORTS
# =====================================================

# =====================================================
# UPLOAD REPORTS
# =====================================================

@app.route('/upload', methods=['GET', 'POST'])

def upload():

    if 'username' not in session:
        return redirect('/')

    if request.method == 'POST':

        common_tags = request.form.get(
            'common_tags'
        )

        # ============================================
        # SAVE GLOBAL TAXONOMY
        # ============================================

        existing_taxonomy = GlobalTaxonomy.query.first()

        if not existing_taxonomy:

            taxonomy = GlobalTaxonomy(
                tags=common_tags
            )

            db.session.add(taxonomy)

        else:

            existing_taxonomy.tags = common_tags

        # ============================================
        # READ FILE
        # ============================================

        file = request.files['file']

        if file.filename.endswith('.csv'):

            df = pd.read_csv(file)

        else:

            df = pd.read_excel(file)

        # ============================================
        # GET EMPLOYEES
        # ============================================

        employees = Employee.query.filter_by(
            role="employee"
        ).all()

        if len(employees) == 0:

            return "No Employees Found"

        employee_index = 0

        # ============================================
        # STORE REPORTS
        # ============================================

        for _, row in df.iterrows():

            report_exists = Report.query.filter_by(
                report_id=str(row['report_id'])
            ).first()

            if not report_exists:

                assigned_employee = employees[
                    employee_index % len(employees)
                ]

                report = Report(

                    report_id=str(row['report_id']),

                    content=str(row['content']),

                    bucket=str(row['bucket']),

                    assigned_to=assigned_employee.username,

                    status="Pending"
                )

                db.session.add(report)

                employee_index += 1

        db.session.commit()

        return redirect('/admin')

    return render_template('upload.html')


# =====================================================
# EMPLOYEE DASHBOARD
# =====================================================

@app.route('/employee')

def employee():

    if 'username' not in session:
        return redirect('/')

    username = session['username']

    print("Logged in user:", username)

    # ================================================
    # CURRENT REPORT
    # ================================================

    report = Report.query.filter(

        Report.assigned_to == username,

        Report.status.in_([
            "Pending",
            "In Progress"
        ])

    ).first()

    if report:

        if report.status == "Pending":

            report.status = "In Progress"

            db.session.commit()

    # ================================================
    # COUNTS
    # ================================================

    completed_count = Report.query.filter_by(
        assigned_to=username,
        status="Completed"
    ).count()

    pending_count = Report.query.filter(

        Report.assigned_to == username,

        Report.status.in_([
            "Pending",
            "In Progress"
        ])

    ).count()

    qc_returned_count = Report.query.filter_by(
        assigned_to=username,
        mismatch=True
    ).count()

    # ================================================
    # GLOBAL TAGS
    # ================================================

    taxonomy = GlobalTaxonomy.query.first()

    if taxonomy:

        tags = taxonomy.tags.splitlines()

    else:

        tags = []

    # ================================================
    # RENDER
    # ================================================

    return render_template(

        'employee.html',

        report=report,

        completed_count=completed_count,

        pending_count=pending_count,

        qc_returned_count=qc_returned_count,

        tags=tags
    )

    # ================================================
    # CHECK EXISTING ASSIGNED REPORT
    # ================================================

    report = Report.query.filter(
        Report.assigned_to == username,
        Report.status.in_([
            "Pending",
            "In Progress"
        ])
    ).first()

    if report:
        if report.status == "Pending":
            report.status = "In Progress"
            db.session.commit()

    # ================================================
    # ASSIGN NEW REPORT
    # ================================================

    completed_count = Report.query.filter_by(
        assigned_to=username,
        status="Completed"
    ).count()

    pending_count = Report.query.filter(

    Report.assigned_to == username,

    Report.status.in_([
        "Pending",
        "In Progress"
    ])

).count()

    qc_returned_count = Report.query.filter_by(
        assigned_to=username,
        mismatch=True
    ).count()

    return render_template(
        'employee.html',
        report=report,
        completed_count=completed_count,
        pending_count=pending_count,
        qc_returned_count=qc_returned_count
    )


# =====================================================
# SUBMIT REPORT
# =====================================================

@app.route('/submit/<int:id>', methods=['POST'])

def submit(id):

    if 'username' not in session:
        return redirect('/')

    username = session['username']

    report = Report.query.filter_by(

        id=id,

        assigned_to=username

    ).first()

    if report:
        selected_tags = request.form.getlist(
            'tags'
        )
        report.selected_tags = ", ".join(
            selected_tags
        )
        sample = random.randint(1, 100)

        if sample <= 20:
            report.qc_required = True
            employee = Employee.query.filter_by(
                username=report.assigned_to
            ).first()

            if employee:
                report.qc_assigned_to = employee.qc_owner
            else:
                report.qc_assigned_to = None

            report.status = "QC Pending"
        else:
            report.status = "Completed"

        db.session.commit()

    return redirect('/employee')


# =====================================================
# ESCALATE REPORT
# =====================================================

@app.route('/escalate/<int:id>', methods=['POST'])

def escalate(id):

    if 'username' not in session:
        return redirect('/')

    username = session['username']

    report = Report.query.filter_by(

        id=id,

        assigned_to=username

    ).first()

    if report:

        report.status = "Escalated"

        team_lead = Employee.query.filter_by(
            role="team_lead"
        ).first()

        if team_lead:

            report.qc_assigned_to = team_lead.username

        db.session.commit()

    return redirect('/employee')

# =====================================================
# QUALITY REVIEWER DASHBOARD
# =====================================================

@app.route('/quality-reviewer')

def quality_reviewer():

    if 'username' not in session:
        return redirect('/')

    reports = Report.query.filter_by(

        status="QC Pending",

        qc_assigned_to=session['username']

    ).all()

    return render_template(
        'reviewer.html',
        reports=reports
    )
# =====================================================
# TEAM LEAD DASHBOARD
# =====================================================

@app.route('/team-lead')

def team_lead():

    if 'username' not in session:
        return redirect('/')

    reports = Report.query.filter_by(

        status="Escalated",

        qc_assigned_to=session['username']

    ).all()

    return render_template(

        'team_lead.html',

        reports=reports
    )    
# =====================================================
# PUBLIC QUALITY DASHBOARD
# =====================================================

@app.route('/quality-dashboard')

def quality_dashboard():

    total_qc_reports = Report.query.filter(

    Report.qc_required == True

).count()

    mismatch_reports = Report.query.filter_by(
        mismatch=True
    ).count()

    valid_appeals = Report.query.filter_by(
        appeal_status="YES"
    ).count()

    qc_pending = Report.query.filter_by(
        status="QC Pending"
    ).count()

    completed_reports = Report.query.filter_by(
        status="Completed"
    ).count()

    # ============================================
    # PRE APPEAL QUALITY
    # ============================================

    if total_qc_reports > 0:

        pre_quality = (
            (
                total_qc_reports
                - mismatch_reports
            )
            / total_qc_reports
        ) * 100

    else:

        pre_quality = 0

    # ============================================
    # POST APPEAL QUALITY
    # ============================================

    if total_qc_reports > 0:

        post_quality = (
            (
                total_qc_reports
                - mismatch_reports
                + valid_appeals
            )
            / total_qc_reports
        ) * 100

    else:

        post_quality = 0

    # ============================================
# EMPLOYEE WISE QUALITY
# ============================================

    employees = Employee.query.filter_by(
        role="employee"
    ).all()

    employee_quality = []

    for employee in employees:

        total = Report.query.filter_by(
            assigned_to=employee.username
        ).count()

        mismatch = Report.query.filter_by(
            assigned_to=employee.username,
            mismatch=True
        ).count()

        valid_appeals = Report.query.filter_by(
            assigned_to=employee.username,
            appeal_status="YES"
        ).count()

        if total > 0:

            pre_quality_emp = (
                (
                    total - mismatch
                ) / total
            ) * 100

            post_quality_emp = (
                (
                    total
                    - mismatch
                    + valid_appeals
                ) / total
            ) * 100

        else:

            pre_quality_emp = 0

            post_quality_emp = 0

        employee_quality.append({

            "employee": employee.username,

            "total": total,

            "mismatch": mismatch,

            "valid_appeals": valid_appeals,

            "pre_quality": round(
                pre_quality_emp,
                2
            ),

            "post_quality": round(
                post_quality_emp,
                2
            )
        })

    return render_template(

        'quality_dashboard.html',

        total_reports=total_qc_reports,

        mismatch_reports=mismatch_reports,

        valid_appeals=valid_appeals,

        qc_pending=qc_pending,

        completed_reports=completed_reports,

        pre_quality=pre_quality,

        post_quality=post_quality,

        total_qc_reports=total_qc_reports,


        employee_quality=employee_quality
    )
# =====================================================
# PRODUCTION DASHBOARD
# =====================================================

@app.route('/production-dashboard')

def production_dashboard():



    reports = Report.query.filter(

        Report.selected_tags != None

    ).all()

    return render_template(

        'production_dashboard.html',

        reports=reports
    )

# =====================================================
# LOGOUT
# =====================================================

@app.route('/logout')

def logout():

    session.clear()

    return redirect('/')

# =====================================================
# RUN
# =====================================================

# =====================================================
# DELETE EMPLOYEE
# =====================================================

@app.route('/delete_employee', methods=['POST'])

def delete_employee():

    username = request.form.get(
        'employee_id'
    )

    employee = Employee.query.filter_by(
        username=username
    ).first()

    if employee:

        db.session.delete(employee)

        db.session.commit()

    return redirect('/admin')

if __name__ == '__main__':

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )