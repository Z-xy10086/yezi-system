import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key_leaf_disease_detection_2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    OUTPUT_FOLDER = os.path.join(basedir, 'output')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}
    
    CAPTCHA_WIDTH = 280
    CAPTCHA_HEIGHT = 120
    SLIDER_WIDTH = 50
    SLIDER_HEIGHT = 50