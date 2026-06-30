import os
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import cv2
import numpy as np

from app.extensions import db
from app.models import Detection
from app.config import Config

farmer = Blueprint('farmer', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def segment_leaf(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    max_contour = max(contours, key=cv2.contourArea)
    
    leaf_mask = np.zeros_like(mask)
    cv2.drawContours(leaf_mask, [max_contour], -1, 255, -1)
    
    return leaf_mask

def detect_lesions(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_brown = np.array([10, 50, 50])
    upper_brown = np.array([40, 255, 200])
    
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([40, 255, 255])
    
    mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    lesion_mask = cv2.bitwise_or(mask_brown, mask_yellow)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    return lesion_mask

def calculate_area_ratio(leaf_mask, lesion_mask):
    leaf_area = np.sum(leaf_mask > 0)
    lesion_area = np.sum(lesion_mask > 0)
    
    if leaf_area > 0:
        ratio = (lesion_area / leaf_area) * 100
    else:
        ratio = 0
    
    return leaf_area, lesion_area, ratio

def draw_results(image, leaf_mask, lesion_mask):
    result = image.copy()
    
    contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 10:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 0, 255), 2)
    
    leaf_contours, _ = cv2.findContours(leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(result, leaf_contours, -1, (0, 255, 0), 3)
    
    return result

@farmer.route('/')
@login_required
def index():
    if current_user.role != 'farmer':
        abort(403)
    
    detections = Detection.query.filter_by(user_id=current_user.id).order_by(Detection.created_at.desc()).all()
    return render_template('farmer/index.html', detections=detections)

@farmer.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if current_user.role != 'farmer':
        abort(403)
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('未选择文件', 'danger')
            return render_template('farmer/upload.html')
        
        file = request.files['file']
        
        if file.filename == '':
            flash('未选择文件', 'danger')
            return render_template('farmer/upload.html')
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = str(int(os.path.getctime(__file__))) + '_' + filename
            upload_path = os.path.join(Config.UPLOAD_FOLDER, timestamp)
            
            file.save(upload_path)
            
            img_array = np.fromfile(upload_path, dtype=np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            leaf_mask = segment_leaf(image)
            
            if leaf_mask is None:
                flash('未检测到叶片区域', 'danger')
                os.remove(upload_path)
                return render_template('farmer/upload.html')
            
            lesion_mask = detect_lesions(image)
            
            leaf_area, lesion_area, ratio = calculate_area_ratio(leaf_mask, lesion_mask)
            
            result_image = draw_results(image, leaf_mask, lesion_mask)
            result_filename = 'result_' + timestamp
            result_path = os.path.join(Config.OUTPUT_FOLDER, result_filename)
            
            success, encoded = cv2.imencode('.png', result_image)
            if success:
                encoded.tofile(result_path)
            
            detection = Detection(
                user_id=current_user.id,
                image_path=upload_path,
                leaf_area=leaf_area,
                lesion_area=lesion_area,
                lesion_ratio=ratio,
                result_image=result_path,
                status='done'
            )
            
            db.session.add(detection)
            db.session.commit()
            
            flash('检测完成', 'success')
            return redirect(url_for('farmer.result', id=detection.id))
        else:
            flash('不支持的文件格式', 'danger')
            return render_template('farmer/upload.html')
    
    return render_template('farmer/upload.html')

@farmer.route('/result/<int:id>')
@login_required
def result(id):
    if current_user.role != 'farmer':
        abort(403)
    
    detection = Detection.query.get_or_404(id)
    
    if detection.user_id != current_user.id:
        abort(403)
    
    original_filename = os.path.basename(detection.image_path)
    
    severity = '轻度'
    advice = '当前病斑较轻，建议加强田间管理，及时清除病叶，合理施肥增强植株抵抗力。'
    
    if detection.lesion_ratio >= 30:
        severity = '重度'
        advice = '病斑严重，建议立即采取化学防治措施，使用合适的杀菌剂进行喷雾防治。'
    elif detection.lesion_ratio >= 15:
        severity = '中度'
        advice = '病斑中等，建议加强监测，可考虑使用生物防治或低浓度化学药剂进行防治。'
    
    return render_template('farmer/result.html', detection=detection, 
                           severity=severity, advice=advice, 
                           original_filename=original_filename)

@farmer.route('/detections')
@login_required
def detections():
    if current_user.role != 'farmer':
        abort(403)
    
    detections = Detection.query.filter_by(user_id=current_user.id).order_by(Detection.created_at.desc()).all()
    return render_template('farmer/detections.html', detections=detections)

@farmer.route('/detection/<int:id>/delete', methods=['POST'])
@login_required
def delete_detection(id):
    if current_user.role != 'farmer':
        abort(403)
    
    detection = Detection.query.get_or_404(id)
    
    if detection.user_id != current_user.id:
        abort(403)
    
    try:
        if os.path.exists(detection.image_path):
            os.remove(detection.image_path)
        if detection.result_image and os.path.exists(detection.result_image):
            os.remove(detection.result_image)
    except:
        pass
    
    db.session.delete(detection)
    db.session.commit()
    
    flash('检测记录已删除', 'success')
    return redirect(url_for('farmer.index'))