import os
import random
import string
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import cv2
import numpy as np

from app.extensions import db
from app.models import User
from app.config import Config

auth = Blueprint('auth', __name__)

def generate_captcha():
    width = Config.CAPTCHA_WIDTH
    height = Config.CAPTCHA_HEIGHT
    slider_width = Config.SLIDER_WIDTH
    
    bg = np.ones((height, width, 3), dtype=np.uint8) * 240
    
    for _ in range(50):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        bg[y, x] = [random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)]
    
    for _ in range(10):
        start_x = random.randint(0, width - 50)
        start_y = random.randint(0, height - 20)
        end_x = start_x + random.randint(20, 50)
        end_y = start_y + random.randint(5, 20)
        cv2.rectangle(bg, (start_x, start_y), (end_x, end_y), 
                      (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)), 
                      thickness=1)
    
    gap_x = random.randint(slider_width * 3, width - slider_width * 2)
    gap_y = (height - slider_width) // 2
    
    trap_x = slider_width * 2
    trap_y = gap_y
    
    trap_center_x = trap_x + slider_width // 2
    trap_center_y = trap_y + slider_width // 2
    trap_radius = slider_width // 2
    
    cv2.circle(bg, (trap_center_x, trap_center_y), trap_radius, 
               (230, 230, 230), thickness=-1)
    
    cv2.circle(bg, (trap_center_x, trap_center_y), trap_radius, 
               (180, 180, 180), thickness=1)
    
    cv2.rectangle(bg, (gap_x, gap_y), (gap_x + slider_width, gap_y + slider_width), 
                  (255, 255, 255), thickness=-1)
    
    slider = np.ones((slider_width, slider_width, 3), dtype=np.uint8) * 255
    
    cv2.rectangle(slider, (0, 0), (slider_width - 1, slider_width - 1), 
                  (45, 136, 253), thickness=2)
    
    slider_center_y = slider_width // 2
    cv2.circle(slider, (slider_width // 2, slider_center_y), 12, (45, 136, 253), thickness=-1)
    cv2.circle(slider, (slider_width // 2, slider_center_y), 8, (255, 255, 255), thickness=-1)
    
    _, bg_encoded = cv2.imencode('.png', bg)
    _, slider_encoded = cv2.imencode('.png', slider)
    
    bg_base64 = bg_encoded.tobytes().hex()
    slider_base64 = slider_encoded.tobytes().hex()
    
    session['captcha_gap_x'] = gap_x
    session['captcha_gap_y'] = gap_y
    session['captcha_token'] = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    return {
        'bg_image': bg_base64,
        'slider_image': slider_base64,
        'slider_width': slider_width,
        'gap_y': gap_y,
        'token': session['captcha_token']
    }

@auth.route('/captcha', methods=['GET'])
def captcha():
    data = generate_captcha()
    return jsonify(data)

@auth.route('/captcha/verify', methods=['POST'])
def verify_captcha():
    try:
        data = request.get_json()
        token = data.get('token')
        slider_x = data.get('slider_x', 0)
        
        if token != session.get('captcha_token'):
            return jsonify({'success': False, 'message': '验证码已过期'})
        
        gap_x = session.get('captcha_gap_x', 0)
        tolerance = 15
        
        if abs(slider_x - gap_x) <= tolerance:
            session['captcha_verified'] = True
            return jsonify({'success': True, 'message': '验证成功'})
        else:
            return jsonify({'success': False, 'message': '验证失败，请重新尝试'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.index'))
        else:
            return redirect(url_for('farmer.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('请填写用户名和密码', 'danger')
            return render_template('auth/login.html')
        
        if not session.get('captcha_verified'):
            flash('请完成滑块验证', 'danger')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            session.pop('captcha_verified', None)
            
            if user.role == 'admin':
                return redirect(url_for('admin.index'))
            else:
                return redirect(url_for('farmer.index'))
        else:
            flash('用户名或密码错误', 'danger')
            session.pop('captcha_verified', None)
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('farmer.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        if not username or not password:
            flash('请填写用户名和密码', 'danger')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('密码长度至少为6位', 'danger')
            return render_template('auth/register.html')
        
        if not session.get('captcha_verified'):
            flash('请完成滑块验证', 'danger')
            return render_template('auth/register.html')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在', 'danger')
            return render_template('auth/register.html')
        
        new_user = User(username=username, role='farmer', phone=phone, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        session.pop('captcha_verified', None)
        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('auth.login'))