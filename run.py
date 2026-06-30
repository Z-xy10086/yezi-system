import os
import sys
from app import create_app, db
from app.models import User

app = create_app()

@app.cli.command('init-db')
def init_db():
    os.makedirs('data', exist_ok=True)
    db.create_all()
    
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', role='admin')
        admin.set_password('123456')
        db.session.add(admin)
        db.session.commit()
        print('管理员账号创建成功: admin/123456')
    else:
        print('管理员账号已存在')
    
    print('数据库初始化完成')

if __name__ == '__main__':
    with app.app_context():
        os.makedirs('data', exist_ok=True)
        os.makedirs('uploads', exist_ok=True)
        os.makedirs('output', exist_ok=True)
        db.create_all()
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('管理员账号创建成功: admin/admin123')
    
    app.run(host='0.0.0.0', port=5000, debug=True)