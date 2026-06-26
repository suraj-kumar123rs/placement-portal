from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'placement-portal-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─────────────────────────── MODELS ───────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / company / student
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    hr_contact = db.Column(db.String(150))
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    approval_status = db.Column(db.String(20), default='Pending')  # Pending / Approved / Rejected
    is_blacklisted = db.Column(db.Boolean, default=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    branch = db.Column(db.String(100))
    year = db.Column(db.Integer)
    cgpa = db.Column(db.Float)
    phone = db.Column(db.String(20))
    resume_filename = db.Column(db.String(200))
    is_blacklisted = db.Column(db.Boolean, default=False)

class PlacementDrive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text)
    required_branch = db.Column(db.String(100))
    required_cgpa = db.Column(db.Float, default=0.0)
    required_year = db.Column(db.Integer)
    deadline = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Pending')  # Pending / Approved / Closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Applied')  # Applied / Shortlisted / Selected / Rejected

# ─────────────────────────── HELPERS ───────────────────────────

def get_current_user():
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])

def login_required(role=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Not authenticated'}), 401
            if role and user.role != role:
                return jsonify({'error': 'Unauthorized'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─────────────────────────── AUTH ROUTES ───────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    role = data.get('role')
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password or role not in ['student', 'company']:
        return jsonify({'error': 'Invalid data'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    user = User(email=email, password=generate_password_hash(password), role=role)
    db.session.add(user)
    db.session.flush()

    if role == 'student':
        student = Student(
            user_id=user.id,
            name=data.get('name', ''),
            branch=data.get('branch', ''),
            year=int(data.get('year', 1)),
            cgpa=float(data.get('cgpa', 0.0)),
            phone=data.get('phone', '')
        )
        db.session.add(student)
    elif role == 'company':
        company = Company(
            user_id=user.id,
            name=data.get('company_name', ''),
            hr_contact=data.get('hr_contact', ''),
            website=data.get('website', ''),
            description=data.get('description', '')
        )
        db.session.add(company)

    db.session.commit()
    return jsonify({'message': 'Registered successfully. Please wait for approval (companies) or login (students).'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 403

    session['user_id'] = user.id
    session['role'] = user.role

    extra = {}
    if user.role == 'company':
        co = Company.query.filter_by(user_id=user.id).first()
        if co and co.is_blacklisted:
            return jsonify({'error': 'Company is blacklisted'}), 403
        extra = {'company_id': co.id if co else None, 'approval_status': co.approval_status if co else None}
    elif user.role == 'student':
        st = Student.query.filter_by(user_id=user.id).first()
        if st and st.is_blacklisted:
            return jsonify({'error': 'Student is blacklisted'}), 403
        extra = {'student_id': st.id if st else None}

    return jsonify({'message': 'Login successful', 'role': user.role, 'email': user.email, **extra})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/me')
def me():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    data = {'id': user.id, 'email': user.email, 'role': user.role}
    if user.role == 'student':
        st = Student.query.filter_by(user_id=user.id).first()
        if st:
            data['student'] = {'id': st.id, 'name': st.name, 'branch': st.branch, 'year': st.year, 'cgpa': st.cgpa, 'phone': st.phone}
    elif user.role == 'company':
        co = Company.query.filter_by(user_id=user.id).first()
        if co:
            data['company'] = {'id': co.id, 'name': co.name, 'approval_status': co.approval_status}
    return jsonify(data)

# ─────────────────────────── ADMIN ROUTES ───────────────────────────

@app.route('/api/admin/dashboard')
def admin_dashboard():
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({
        'total_students': Student.query.count(),
        'total_companies': Company.query.count(),
        'total_drives': PlacementDrive.query.count(),
        'pending_companies': Company.query.filter_by(approval_status='Pending').count(),
        'pending_drives': PlacementDrive.query.filter_by(status='Pending').count(),
        'total_applications': Application.query.count()
    })

@app.route('/api/admin/companies')
def admin_companies():
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    search = request.args.get('search', '')
    q = Company.query
    if search:
        q = q.filter(Company.name.ilike(f'%{search}%'))
    companies = q.all()
    result = []
    for c in companies:
        u = User.query.get(c.user_id)
        result.append({
            'id': c.id, 'name': c.name, 'hr_contact': c.hr_contact,
            'website': c.website, 'approval_status': c.approval_status,
            'is_blacklisted': c.is_blacklisted, 'email': u.email if u else ''
        })
    return jsonify(result)

@app.route('/api/admin/companies/<int:cid>/approve', methods=['POST'])
def approve_company(cid):
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    action = data.get('action')  # approve / reject
    co = Company.query.get_or_404(cid)
    co.approval_status = 'Approved' if action == 'approve' else 'Rejected'
    db.session.commit()
    return jsonify({'message': f'Company {co.approval_status}'})

@app.route('/api/admin/companies/<int:cid>/blacklist', methods=['POST'])
def blacklist_company(cid):
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    co = Company.query.get_or_404(cid)
    co.is_blacklisted = not co.is_blacklisted
    db.session.commit()
    return jsonify({'message': 'Updated', 'is_blacklisted': co.is_blacklisted})

@app.route('/api/admin/students')
def admin_students():
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    search = request.args.get('search', '')
    q = Student.query
    if search:
        q = q.filter(Student.name.ilike(f'%{search}%'))
    students = q.all()
    result = []
    for s in students:
        u = User.query.get(s.user_id)
        result.append({
            'id': s.id, 'name': s.name, 'branch': s.branch,
            'year': s.year, 'cgpa': s.cgpa, 'phone': s.phone,
            'is_blacklisted': s.is_blacklisted, 'email': u.email if u else ''
        })
    return jsonify(result)

@app.route('/api/admin/students/<int:sid>/blacklist', methods=['POST'])
def blacklist_student(sid):
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    st = Student.query.get_or_404(sid)
    st.is_blacklisted = not st.is_blacklisted
    db.session.commit()
    return jsonify({'message': 'Updated', 'is_blacklisted': st.is_blacklisted})

@app.route('/api/admin/drives')
def admin_drives():
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    drives = PlacementDrive.query.all()
    result = []
    for d in drives:
        co = Company.query.get(d.company_id)
        result.append({
            'id': d.id, 'job_title': d.job_title, 'job_description': d.job_description,
            'company_name': co.name if co else '', 'company_id': d.company_id,
            'required_branch': d.required_branch, 'required_cgpa': d.required_cgpa,
            'required_year': d.required_year,
            'deadline': d.deadline.strftime('%Y-%m-%d') if d.deadline else '',
            'status': d.status,
            'applicants': Application.query.filter_by(drive_id=d.id).count()
        })
    return jsonify(result)

@app.route('/api/admin/drives/<int:did>/approve', methods=['POST'])
def approve_drive(did):
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    action = data.get('action')
    drive = PlacementDrive.query.get_or_404(did)
    drive.status = 'Approved' if action == 'approve' else 'Closed'
    db.session.commit()
    return jsonify({'message': f'Drive {drive.status}'})

@app.route('/api/admin/applications')
def admin_applications():
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    apps = Application.query.all()
    result = []
    for a in apps:
        st = Student.query.get(a.student_id)
        dr = PlacementDrive.query.get(a.drive_id)
        co = Company.query.get(dr.company_id) if dr else None
        result.append({
            'id': a.id, 'student_name': st.name if st else '',
            'drive_title': dr.job_title if dr else '',
            'company_name': co.name if co else '',
            'applied_at': a.applied_at.strftime('%Y-%m-%d'),
            'status': a.status
        })
    return jsonify(result)

# ─────────────────────────── COMPANY ROUTES ───────────────────────────

@app.route('/api/company/dashboard')
def company_dashboard():
    user = get_current_user()
    if not user or user.role != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    co = Company.query.filter_by(user_id=user.id).first()
    if not co:
        return jsonify({'error': 'Company not found'}), 404
    drives = PlacementDrive.query.filter_by(company_id=co.id).all()
    drives_data = []
    for d in drives:
        drives_data.append({
            'id': d.id, 'job_title': d.job_title, 'status': d.status,
            'deadline': d.deadline.strftime('%Y-%m-%d') if d.deadline else '',
            'applicants': Application.query.filter_by(drive_id=d.id).count()
        })
    return jsonify({
        'company': {'id': co.id, 'name': co.name, 'approval_status': co.approval_status,
                    'hr_contact': co.hr_contact, 'website': co.website},
        'drives': drives_data,
        'total_applicants': sum(d['applicants'] for d in drives_data)
    })

@app.route('/api/company/drives', methods=['POST'])
def create_drive():
    user = get_current_user()
    if not user or user.role != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    co = Company.query.filter_by(user_id=user.id).first()
    if not co or co.approval_status != 'Approved':
        return jsonify({'error': 'Company not approved yet'}), 403
    data = request.get_json()
    deadline = None
    if data.get('deadline'):
        deadline = datetime.strptime(data['deadline'], '%Y-%m-%d')
    drive = PlacementDrive(
        company_id=co.id,
        job_title=data.get('job_title', ''),
        job_description=data.get('job_description', ''),
        required_branch=data.get('required_branch', ''),
        required_cgpa=float(data.get('required_cgpa', 0.0)),
        required_year=int(data.get('required_year', 0)) if data.get('required_year') else None,
        deadline=deadline
    )
    db.session.add(drive)
    db.session.commit()
    return jsonify({'message': 'Drive created. Awaiting admin approval.'}), 201

@app.route('/api/company/applications')
def company_applications():
    user = get_current_user()
    if not user or user.role != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    co = Company.query.filter_by(user_id=user.id).first()
    drive_id = request.args.get('drive_id')
    drives = PlacementDrive.query.filter_by(company_id=co.id).all()
    drive_ids = [d.id for d in drives]
    q = Application.query.filter(Application.drive_id.in_(drive_ids))
    if drive_id:
        q = q.filter_by(drive_id=int(drive_id))
    apps = q.all()
    result = []
    for a in apps:
        st = Student.query.get(a.student_id)
        dr = PlacementDrive.query.get(a.drive_id)
        result.append({
            'id': a.id, 'student_name': st.name if st else '',
            'student_branch': st.branch if st else '', 'student_cgpa': st.cgpa if st else 0,
            'drive_title': dr.job_title if dr else '', 'drive_id': a.drive_id,
            'applied_at': a.applied_at.strftime('%Y-%m-%d'), 'status': a.status
        })
    return jsonify(result)

@app.route('/api/company/applications/<int:aid>/status', methods=['POST'])
def update_application_status(aid):
    user = get_current_user()
    if not user or user.role != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    app_obj = Application.query.get_or_404(aid)
    app_obj.status = data.get('status', app_obj.status)
    db.session.commit()
    return jsonify({'message': 'Status updated'})

# ─────────────────────────── STUDENT ROUTES ───────────────────────────

@app.route('/api/student/dashboard')
def student_dashboard():
    user = get_current_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    st = Student.query.filter_by(user_id=user.id).first()
    if not st:
        return jsonify({'error': 'Student not found'}), 404

    # Get approved drives
    branch_filter = request.args.get('branch', '')
    cgpa_filter = request.args.get('cgpa', '')

    q = PlacementDrive.query.filter_by(status='Approved')
    if branch_filter:
        q = q.filter(PlacementDrive.required_branch.ilike(f'%{branch_filter}%'))
    if cgpa_filter:
        q = q.filter(PlacementDrive.required_cgpa <= float(cgpa_filter))

    drives = q.all()
    applied_ids = [a.drive_id for a in Application.query.filter_by(student_id=st.id).all()]

    drives_data = []
    for d in drives:
        co = Company.query.get(d.company_id)
        drives_data.append({
            'id': d.id, 'job_title': d.job_title, 'job_description': d.job_description,
            'company_name': co.name if co else '',
            'required_branch': d.required_branch, 'required_cgpa': d.required_cgpa,
            'required_year': d.required_year,
            'deadline': d.deadline.strftime('%Y-%m-%d') if d.deadline else '',
            'already_applied': d.id in applied_ids
        })

    # Applications history
    apps = Application.query.filter_by(student_id=st.id).all()
    apps_data = []
    for a in apps:
        dr = PlacementDrive.query.get(a.drive_id)
        co = Company.query.get(dr.company_id) if dr else None
        apps_data.append({
            'id': a.id, 'drive_title': dr.job_title if dr else '',
            'company_name': co.name if co else '',
            'applied_at': a.applied_at.strftime('%Y-%m-%d'), 'status': a.status
        })

    return jsonify({
        'student': {'id': st.id, 'name': st.name, 'branch': st.branch, 'year': st.year,
                    'cgpa': st.cgpa, 'phone': st.phone, 'email': user.email},
        'drives': drives_data,
        'applications': apps_data
    })

@app.route('/api/student/apply/<int:drive_id>', methods=['POST'])
def apply_drive(drive_id):
    user = get_current_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    st = Student.query.filter_by(user_id=user.id).first()
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.status != 'Approved':
        return jsonify({'error': 'Drive not available'}), 400
    existing = Application.query.filter_by(student_id=st.id, drive_id=drive_id).first()
    if existing:
        return jsonify({'error': 'Already applied'}), 400
    app_obj = Application(student_id=st.id, drive_id=drive_id)
    db.session.add(app_obj)
    db.session.commit()
    return jsonify({'message': 'Applied successfully!'}), 201

@app.route('/api/student/profile', methods=['POST'])
def update_profile():
    user = get_current_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    st = Student.query.filter_by(user_id=user.id).first()
    data = request.get_json()
    st.name = data.get('name', st.name)
    st.branch = data.get('branch', st.branch)
    st.year = int(data.get('year', st.year))
    st.cgpa = float(data.get('cgpa', st.cgpa))
    st.phone = data.get('phone', st.phone)
    db.session.commit()
    return jsonify({'message': 'Profile updated'})

# ─────────────────────────── INIT DB ───────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        # Create admin if not exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                email='admin@placement.com',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin created: admin@placement.com / admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
