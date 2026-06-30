from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from functools import wraps

from app.extensions import db
from app.models import User, Detection

admin = Blueprint('admin', __name__)

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@admin.route('/')
@login_required
@role_required('admin')
def index():
    total_users = User.query.count()
    total_detections = Detection.query.count()
    today_detections = Detection.query.filter(
        Detection.created_at >= Detection.created_at.now().date()
    ).count()
    
    recent_detections = Detection.query.order_by(Detection.created_at.desc()).limit(10).all()
    
    return render_template('admin/index.html', 
                           total_users=total_users,
                           total_detections=total_detections,
                           today_detections=today_detections,
                           recent_detections=recent_detections)

@admin.route('/users')
@login_required
@role_required('admin')
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'farmer')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        if not username or not password:
            flash('请填写用户名和密码', 'danger')
            return render_template('admin/user_edit.html', action='add')
        
        if len(password) < 6:
            flash('密码长度至少为6位', 'danger')
            return render_template('admin/user_edit.html', action='add')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在', 'danger')
            return render_template('admin/user_edit.html', action='add')
        
        new_user = User(username=username, role=role, phone=phone, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('用户添加成功', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_edit.html', action='add')

@admin.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(id):
    user = User.query.get_or_404(id)
    
    if user.role == 'admin' and current_user.id != user.id:
        flash('不能编辑其他管理员', 'danger')
        return redirect(url_for('admin.users'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'farmer')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        if not username:
            flash('请填写用户名', 'danger')
            return render_template('admin/user_edit.html', action='edit', user=user)
        
        existing_user = User.query.filter(User.username == username, User.id != id).first()
        if existing_user:
            flash('用户名已存在', 'danger')
            return render_template('admin/user_edit.html', action='edit', user=user)
        
        user.username = username
        user.role = role
        user.phone = phone
        user.email = email
        
        if password:
            if len(password) < 6:
                flash('密码长度至少为6位', 'danger')
                return render_template('admin/user_edit.html', action='edit', user=user)
            user.set_password(password)
        
        db.session.commit()
        
        flash('用户信息更新成功', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_edit.html', action='edit', user=user)

@admin.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(id):
    user = User.query.get_or_404(id)
    
    if user.role == 'admin':
        flash('不能删除管理员', 'danger')
        return redirect(url_for('admin.users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('用户已删除', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/stats')
@login_required
@role_required('admin')
def stats():
    total_users = User.query.count()
    farmer_count = User.query.filter_by(role='farmer').count()
    admin_count = User.query.filter_by(role='admin').count()
    
    total_detections = Detection.query.count()
    done_detections = Detection.query.filter_by(status='done').count()
    
    avg_ratio = 0
    if done_detections > 0:
        total_ratio = db.session.query(db.func.sum(Detection.lesion_ratio)).scalar() or 0
        avg_ratio = total_ratio / done_detections
    
    recent_detections = Detection.query.order_by(Detection.created_at.desc()).limit(20).all()
    
    return render_template('admin/stats.html',
                           total_users=total_users,
                           farmer_count=farmer_count,
                           admin_count=admin_count,
                           total_detections=total_detections,
                           done_detections=done_detections,
                           avg_ratio=avg_ratio,
                           recent_detections=recent_detections)

@admin.route('/detection/<int:id>')
@login_required
@role_required('admin')
def view_detection(id):
    detection = Detection.query.get_or_404(id)
    user = detection.user
    
    severity = '轻度'
    advice = '当前病斑较轻，建议加强田间管理，及时清除病叶，合理施肥增强植株抵抗力。'
    
    if detection.lesion_ratio >= 30:
        severity = '重度'
        advice = '病斑严重，建议立即采取化学防治措施，使用合适的杀菌剂进行喷雾防治。'
    elif detection.lesion_ratio >= 15:
        severity = '中度'
        advice = '病斑中等，建议加强监测，可考虑使用生物防治或低浓度化学药剂进行防治。'
    
    return render_template('admin/detection_detail.html', 
                           detection=detection, user=user,
                           severity=severity, advice=advice)