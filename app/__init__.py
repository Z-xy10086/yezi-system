import os
from flask import Flask

from app.config import Config
from app.extensions import db, login_manager

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    login_manager.init_app(app)
    
    from app.blueprints.auth import auth as auth_bp
    app.register_blueprint(auth_bp)
    
    from app.blueprints.farmer import farmer as farmer_bp
    app.register_blueprint(farmer_bp, url_prefix='/farmer')
    
    from app.blueprints.admin import admin as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.index'))
            else:
                return redirect(url_for('farmer.index'))
        return redirect(url_for('auth.login'))
    
    from flask import redirect, url_for
    
    return app