# =====================================================
# IMPORTS
# =====================================================

from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import random
import os
import secrets

import pandas as pd

from database import db

from models import (

    Employee,

    Report,

    GlobalTaxonomy
)

# =====================================================
# APP CONFIG
# =====================================================

app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

app.secret_key = secrets.token_hex(16)

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL is None:

    DATABASE_URL = "sqlite:///annotation.db"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# =====================================================
# DATABASE INIT
# =====================================================

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

            else:

                return redirect('/employee')

        else:

            return "Invalid Login"

    return render_template('login.html')

# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route('/admin')

def admin():

    if 'username' not in session:

        return redirect('/')

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

    qc_pending_reports = Report.query.filter_by(
        status="QC Pending"
    ).count()

    employees = Employee.query.all()

    employee_stats = []

    for employee in employees:

        completed_count = Report.query.filter_by(

            assigned_to=employee.username,

            status="Completed"

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

            "pending": pending_count
        })

    return render_template(

        'admin.html',

        total_reports=total_reports,

        pending_reports=pending_reports,

        completed_reports=completed_reports,

        escalated_reports=escalated_reports,

        qc_pending_reports=qc_pending_reports,

        employee_stats=employee_stats
    )

# =====================================================
# CREATE EMPLOYEE
# =====================================================

@app.route('/create_employee', methods=['POST'])

def create_employee():

    username = request.form.get(
        'username'
    ).strip()

    password = request.form.get(
        'password'
    ).strip()

    role = request.form.get(
        'role'
    )

    qc_owner = request.form.get(
        'qc_owner'
    )

    employee_exists = Employee.query.filter_by(
        username=username
    ).first()

    if employee_exists:

        return "Employee Already Exists"

    employee = Employee(

        username=username,

        password=password,

        role=role,

        qc_owner=qc_owner
    )

    db.session.add(employee)

    db.session.commit()

    return redirect('/admin')

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

        existing_taxonomy = GlobalTaxonomy.query.first()

        if existing_taxonomy:

            existing_taxonomy.tags = common_tags

        else:

            taxonomy = GlobalTaxonomy(
                tags=common_tags
            )

            db.session.add(taxonomy)

        file = request.files.get('file')

        if not file:

            return "No File Uploaded"

        # ============================================
        # READ FILE
        # ============================================

        try:

            if file.filename.endswith('.csv'):

                df = pd.read_csv(file)

            else:

                df = pd.read_excel(file)

            df = df.fillna("")

        except Exception as e:

            return f"FILE ERROR: {e}"

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
        # CHUNK UPLOAD
        # ============================================

        chunk_size = 12000

        for start in range(0, len(df), chunk_size):

            chunk = df.iloc[start:start + chunk_size]

            reports_to_add = []

            for _, row in chunk.iterrows():

                try:

                    report_id = str(
                        row.get('report_id', '')
                    ).strip()

                    content = str(
                        row.get('content', '')
                    ).strip()

                    bucket = str(
                        row.get('bucket', '')
                    ).strip()

                    if report_id == '' or content == '':

                        continue

                    report_exists = Report.query.filter_by(
                        report_id=report_id
                    ).first()

                    if report_exists:

                        continue

                    assigned_employee = employees[
                        employee_index % len(employees)
                    ]

                    report = Report(

                        report_id=report_id,

                        content=content,

                        bucket=bucket,

                        assigned_to=assigned_employee.username,

                        status="Pending"
                    )

                    reports_to_add.append(report)

                    employee_index += 1

                except Exception as e:

                    print("ROW ERROR:", e)

            # ========================================
            # BULK INSERT
            # ========================================

            db.session.bulk_save_objects(
                reports_to_add
            )

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

    completed_count = Report.query.filter(

        Report.assigned_to == username,
        Report.selected_tags != None,
         Report.selected_tags != ""


    ).count()

    pending_count = Report.query.filter(

        Report.assigned_to == username,

        ( 
            (Report.selected_tags == None) |
            (Report.selected_tags == "")    
        )

    ).count()

    qc_returned_count = Report.query.filter_by(

        assigned_to=username,

        mismatch=True

    ).count()

    # ================================================
    # TAGS
    # ================================================

    taxonomy = GlobalTaxonomy.query.first()

    tags = []

    if taxonomy and taxonomy.tags:

        raw_tags = taxonomy.tags

        raw_tags = raw_tags.replace(
            '\n',
            ','
        )

        split_tags = raw_tags.split(',')

        seen = set()

        for tag in split_tags:

            clean_tag = tag.strip()

            if not clean_tag:

                continue

            if clean_tag in seen:

                continue

            seen.add(clean_tag)

            tags.append(clean_tag)

    # ================================================
    # SIMILAR REPORTS
    # ================================================

    similar_reports = Report.query.filter(

        Report.selected_tags != None

    ).limit(100).all()

    return render_template(

        'employee.html',

        report=report,

        completed_count=completed_count,

        pending_count=pending_count,

        qc_returned_count=qc_returned_count,

        tags=tags,

        similar_reports=similar_reports
    )

# =====================================================
# SUBMIT REPORT
# =====================================================

@app.route('/submit/<int:id>', methods=['POST'])

def submit(id):

    username = session['username']

    report = Report.query.filter_by(

        id=id,

        assigned_to=username

    ).first()

    if report:

        selected_tags = request.form.getlist(
            'tags'
        )
        action = request.form.get('action')

        if action == "escalate":

            escalation_reason = request.form.get(
                   'escalation_reason'
                )
            report.status = "Escalated"
            report.escalation_reason = escalation_reason

            db.session.commit()

            return redirect('/employee')

        report.selected_tags = ", ".join(
            selected_tags
        )
        report.employee_name = session['username']

        report.employee_timestamp = datetime.now().strftime(
        "%d-%m-%Y %I:%M %p"
        ) 

        sample = random.randint(1, 100)

        if sample <= 5:

            report.qc_required = True

            employee = Employee.query.filter_by(
                username=report.assigned_to
            ).first()

            if employee:

                report.qc_assigned_to = employee.qc_owner

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
# QUALITY REVIEWER
# =====================================================

@app.route('/quality-reviewer')

def quality_reviewer():

    if 'username' not in session:

        return redirect('/')

    reports = Report.query.filter_by(

        status="QC Pending",

        qc_assigned_to=session['username']

    ).all()

    taxonomy = GlobalTaxonomy.query.first()

    tags = []

    if taxonomy and taxonomy.tags:

        raw_tags = taxonomy.tags

        raw_tags = raw_tags.replace('\n', ',')

        split_tags = raw_tags.split(',')

        seen = set()

        for tag in split_tags:

            clean_tag = tag.strip()

            if not clean_tag:

                continue

            if clean_tag in seen:

                continue

            seen.add(clean_tag)

            tags.append(clean_tag)

    return render_template(

        'reviewer.html',

        reports=reports,

        tags=tags
    )

 # =====================================================
 # QC SUBMIT
 # =====================================================

@app.route('/qc-submit/<int:report_id>', methods=['POST'])

def qc_submit(report_id):

    if 'username' not in session:

        return redirect('/')

    report = Report.query.get(report_id)

    if not report:

        return redirect('/quality-reviewer')

    selected_tags = request.form.getlist('tags')

    report.qc_selected_tags = ",".join(selected_tags)

    report.qc_name = session['username']

    report.qc_timestamp = datetime.now().strftime(
     "%d-%m-%Y %I:%M %p"
    )

    employee_tags = []

    if report.selected_tags:

        employee_tags = [

            x.strip()

            for x in report.selected_tags.split(',')

            if x.strip()
        ]

    qc_tags = [

        x.strip()

        for x in selected_tags

        if x.strip()
    ]

    # MISMATCH CHECK

    if set(employee_tags) != set(qc_tags):

        report.mismatch = True

        report.status = "Mismatch"

    else:

        report.status = "QC Passed"

    db.session.commit()

    return redirect('/quality-reviewer')

# =====================================================
# REPORT DETAILS
# =====================================================

@app.route('/report/<int:report_id>')

def report_details(report_id):

    if 'username' not in session:

        return redirect('/')

    report = Report.query.get(report_id)

    return render_template(

        'report_details.html',

        report=report
    )
## =====================================================
# TEAM LEAD DASHBOARD
# =====================================================

@app.route('/team-lead')

def team_lead():

    if 'username' not in session:

        return redirect('/')

    reports = Report.query.filter_by(

        status="Escalated"

    ).all()

    return render_template(

        'team_lead.html',

        reports=reports
    )

# =====================================================
# TL FINAL SUBMIT
# =====================================================

@app.route('/tl-submit/<int:report_id>', methods=['POST'])

def tl_submit(report_id):

    if 'username' not in session:

        return redirect('/')

    report = Report.query.get(report_id)

    tl_tags = request.form.get('tl_tags')

    report.selected_tags = tl_tags

    report.employee_name = session['username']

    report.employee_timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    report.status = "Completed"

    db.session.commit()

    return redirect('/team-lead')

# =====================================================
# PRODUCTION DASHBOARD
# =====================================================

@app.route('/production-dashboard')

def production_dashboard():

    if 'username' not in session:

        return redirect('/')

    reports = Report.query.all()

    total_reports = Report.query.count()

    completed_reports = Report.query.filter(
        Report.status.in_(
            ["Completed", "QC Passed"]
        )
    ).count()

    pending_reports = Report.query.filter(
        Report.status.in_(
            ["Pending", "In Progress"]
        )
    ).count()

    mismatch_reports = Report.query.filter_by(
        mismatch=True
    ).count()

    return render_template(

        'production_dashboard.html',

        reports=reports,

        total_reports=total_reports,

        completed_reports=completed_reports,

        pending_reports=pending_reports,

        mismatch_reports=mismatch_reports
    )

# =====================================================
# QUALITY DASHBOARD
# =====================================================

@app.route('/quality-dashboard')

def quality_dashboard():

    total_qc_reports = Report.query.filter(
        Report.qc_required == True
    ).count()

    mismatch_reports = Report.query.filter_by(
        mismatch=True
    ).count()

    qc_pending = Report.query.filter_by(
        status="QC Pending"
    ).count()

    completed_reports = Report.query.filter_by(
        status="Completed"
    ).count()

    return render_template(

        'quality_dashboard.html',

        total_reports=total_qc_reports,

        mismatch_reports=mismatch_reports,

        qc_pending=qc_pending,

        completed_reports=completed_reports
    )
# =====================================================
# MISMATCH DASHBOARD
# =====================================================

@app.route('/mismatch-dashboard')

def mismatch_dashboard():

    if 'username' not in session:

        return redirect('/')

    reports = Report.query.filter_by(
        mismatch=True
    ).all()

    return render_template(
        'mismatch_dashboard.html',
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

if __name__ == '__main__':

    app.run(

        debug=True,

        host='0.0.0.0',

        port=5000
    )