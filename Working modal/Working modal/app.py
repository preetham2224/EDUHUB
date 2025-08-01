import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__, template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, faculty, student
    department = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    announcements = db.relationship('Announcement', backref='author', lazy=True)
    materials = db.relationship('StudyMaterial', backref='uploader', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy=True)
    leave_applications = db.relationship('LeaveApplication', foreign_keys='LeaveApplication.applicant_id', backref='applicant', lazy=True)
    reviewed_leaves = db.relationship('LeaveApplication', foreign_keys='LeaveApplication.reviewer_id', backref='reviewer', lazy=True)

class LeaveApplication(db.Model):
    __tablename__ = 'leave_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)

class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_urgent = db.Column(db.Boolean, default=False)

class StudyMaterial(db.Model):
    __tablename__ = 'study_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.now)
    subject = db.Column(db.String(100))
    file_type = db.Column(db.String(50))

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.now)
    is_read = db.Column(db.Boolean, default=False)

class Timetable(db.Model):
    __tablename__ = 'timetables'
    
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    time_slot = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    classroom = db.Column(db.String(50))
    department = db.Column(db.String(50))

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    link = db.Column(db.String(200))

# Helper Functions
def login_required(role="any"):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'danger')
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if role != "any":
                if isinstance(role, list):
                    if user.role not in role:
                        flash('You do not have permission to access this page.', 'danger')
                        return redirect(url_for('dashboard'))
                elif user.role != role:
                    flash('You do not have permission to access this page.', 'danger')
                    return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def create_notification(user_id, content, link=None):
    notification = Notification(
        user_id=user_id,
        content=content,
        link=link
    )
    db.session.add(notification)
    db.session.commit()

# Middleware
@app.before_request
def sync_user_role():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.role != session.get('user_role'):
            session['user_role'] = user.role
            flash('Your permissions have been updated', 'info')

# Authentication Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        department = request.form.get('department')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        if role.lower() not in ['student', 'faculty', 'admin']:
            flash('Invalid role specified', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role.lower(),
            department=department
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Dashboard Routes
@app.route('/dashboard')
@login_required(role="any")
def dashboard():
    user = User.query.get(session['user_id'])
    
    # Get unread notifications count
    unread_notifications = Notification.query.filter_by(
        user_id=user.id,
        is_read=False
    ).count()
    
    if user.role == 'admin':
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
        pending_leaves = LeaveApplication.query.filter_by(status='pending').count()
        total_users = User.query.count()
        
        return render_template('admin/dashboard.html', 
                             announcements=announcements,
                             pending_leaves=pending_leaves,
                             total_users=total_users,
                             unread_notifications=unread_notifications)
    
    elif user.role == 'faculty':
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
        unread_messages = Message.query.filter_by(
            recipient_id=user.id,
            is_read=False
        ).count()
        materials = StudyMaterial.query.filter_by(uploaded_by=user.id).order_by(StudyMaterial.uploaded_at.desc()).limit(3).all()
        pending_leaves = LeaveApplication.query.filter_by(status='pending').count()
        
        return render_template('faculty/dashboard.html', 
                             announcements=announcements,
                             unread_messages=unread_messages,
                             materials=materials,
                             pending_leaves=pending_leaves,
                             unread_notifications=unread_notifications)
    
    else:  # student
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
        timetable = Timetable.query.filter_by(department=user.department).all()
        recent_materials = StudyMaterial.query.order_by(StudyMaterial.uploaded_at.desc()).limit(3).all()
        
        return render_template('student/dashboard.html', 
                             announcements=announcements,
                             timetable=timetable,
                             recent_materials=recent_materials,
                             unread_notifications=unread_notifications)

# Announcements Routes
@app.route('/announcements')
@login_required(role="any")
def announcements():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('announcements.html', announcements=announcements)

@app.route('/announcements/new', methods=['GET', 'POST'])
@login_required(role=["faculty", "admin"])
def new_announcement():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        is_urgent = True if request.form.get('is_urgent') else False
        
        announcement = Announcement(
            title=title,
            content=content,
            posted_by=session['user_id'],
            is_urgent=is_urgent
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        # Create notifications for all users
        users = User.query.all()
        for user in users:
            create_notification(
                user.id,
                f"New announcement: {title}",
                url_for('announcements')
            )
        
        flash('Announcement posted successfully!', 'success')
        return redirect(url_for('announcements'))
    
    return render_template('new_announcement.html')

# Study Materials Routes
@app.route('/materials')
@login_required(role="any")
def materials():
    materials = StudyMaterial.query.order_by(StudyMaterial.uploaded_at.desc()).all()
    subjects = list({m.subject for m in materials if m.subject})  # Get unique subjects
    return render_template('student/materials.html', 
                         materials=materials,
                         subjects=subjects)

@app.route('/materials/upload', methods=['GET', 'POST'])
@login_required(role=["faculty", "admin"])
def upload_material():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        subject = request.form.get('subject')
        file_type = request.form.get('file_type')
        file = request.files['file']
        
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            material = StudyMaterial(
                title=title,
                filename=filename,
                description=description,
                uploaded_by=session['user_id'],
                subject=subject,
                file_type=file_type
            )
            
            db.session.add(material)
            db.session.commit()
            
            flash('Material uploaded successfully!', 'success')
            return redirect(url_for('materials'))
    
    return render_template('faculty/upload.html')

@app.route('/materials/download/<int:material_id>')
@login_required(role="any")
def download_material(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], material.filename, as_attachment=True)

# Chat & Feedback Routes
@app.route('/chat')
@login_required(role="any")
def chat():
    user = User.query.get(session['user_id'])
    
    if user.role == 'student':
        faculty = User.query.filter_by(role='faculty').all()
        return render_template('chat.html', faculty=faculty)
    else:
        conversations = db.session.query(
            Message,
            User.name
        ).join(
            User, Message.sender_id == User.id
        ).filter(
            Message.recipient_id == user.id
        ).order_by(
            Message.sent_at.desc()
        ).all()
        
        return render_template('chat.html', conversations=conversations)

@app.route('/chat/send', methods=['POST'])
@login_required(role="any")
def send_message():
    recipient_id = request.form.get('recipient_id')
    content = request.form.get('content')
    
    message = Message(
        sender_id=session['user_id'],
        recipient_id=recipient_id,
        content=content
    )
    
    db.session.add(message)
    db.session.commit()
    
    sender = User.query.get(session['user_id'])
    create_notification(
        recipient_id,
        f"New message from {sender.name}",
        url_for('chat')
    )
    
    flash('Message sent successfully!', 'success')
    return redirect(url_for('chat'))

# Timetable Routes
@app.route('/timetable')
@login_required(role="any")
def timetable():
    user = User.query.get(session['user_id'])
    
    if user.role == 'student':
        timetable = Timetable.query.filter_by(department=user.department).all()
    else:
        timetable = Timetable.query.all()
    
    return render_template('timetable.html', timetable=timetable)

# Leave Application Routes
@app.route('/leave', methods=['GET', 'POST'])
@login_required(role="student")
def leave_application():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        reason = request.form.get('reason')
        
        application = LeaveApplication(
            applicant_id=session['user_id'],
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        
        db.session.add(application)
        db.session.commit()
        
        faculty = User.query.filter_by(role='faculty').all()
        for person in faculty:
            create_notification(
                person.id,
                f"New leave application from {session['user_name']}",
                url_for('manage_leaves')
            )
        
        flash('Leave application submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('leave.html')

@app.route('/leave/manage')
@login_required(role=["faculty", "admin"])
def manage_leaves():
    pending_leaves = db.session.query(
        LeaveApplication,
        User.name
    ).join(
        User, LeaveApplication.applicant_id == User.id
    ).filter(
        LeaveApplication.status == 'pending'
    ).all()
    
    return render_template('manage_leaves.html', pending_leaves=pending_leaves)

@app.route('/leave/decision/<int:leave_id>/<decision>')
@login_required(role=["faculty", "admin"])
def leave_decision(leave_id, decision):
    leave = LeaveApplication.query.get_or_404(leave_id)
    
    if decision not in ['approve', 'reject']:
        flash('Invalid decision', 'danger')
        return redirect(url_for('manage_leaves'))
    
    leave.status = 'approved' if decision == 'approve' else 'rejected'
    leave.reviewer_id = session['user_id']
    leave.reviewed_at = datetime.now()
    
    db.session.commit()
    
    decision_text = "approved" if decision == 'approve' else "rejected"
    create_notification(
        leave.applicant_id,
        f"Your leave application has been {decision_text}",
        url_for('dashboard')
    )
    
    flash(f'Leave application {decision_text}!', 'success')
    return redirect(url_for('manage_leaves'))

# Notification Routes
@app.route('/notifications')
@login_required(role="any")
def notifications():
    notifications = Notification.query.filter_by(
        user_id=session['user_id']
    ).order_by(
        Notification.created_at.desc()
    ).all()
    
    for notification in notifications:
        if not notification.is_read:
            notification.is_read = True
            db.session.commit()
    
    return render_template('notifications.html', notifications=notifications)

# Admin Routes
@app.route('/admin/users')
@login_required(role="admin")
def manage_users():
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/users/delete/<int:user_id>')
@login_required(role="admin")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.role == 'admin':
        flash('Cannot delete admin users', 'danger')
        return redirect(url_for('manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('manage_users'))

# Utility Filters
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ""
    return value.strftime(format)


# Database Management
@app.route('/delete-db')
def delete_db():
    try:
        db_path = 'instance/student_portal.db'
        if os.path.exists(db_path):
            os.remove(db_path)
            return "Database deleted successfully"
        return "Database file not found"
    except Exception as e:
        return f"Error deleting database: {str(e)}"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)