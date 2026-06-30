# 农作物叶片病斑检测系统 - Web界面实操文档

## 一、项目概述

本项目旨在为农作物叶片病斑检测系统构建一个**电脑端和手机端**都可以访问的Web界面。系统包含两种用户角色：

| 角色 | 功能 |
|------|------|
| **农户** | 注册、登录、上传叶片图片、查看检测结果和防治方案 |
| **管理员** | 登录、管理农户账号（增删改查）、查看检测统计 |

## 二、技术栈选择

| 层次 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Flask | 轻量级Python Web框架，适合中小型项目 |
| 数据库 | SQLite | 轻量级数据库，无需额外安装服务 |
| ORM | Flask-SQLAlchemy | 对象关系映射，简化数据库操作 |
| 用户认证 | Flask-Login | 用户登录状态管理 |
| 表单验证 | Flask-WTF | 表单处理与CSRF防护 |
| 前端框架 | Bootstrap 5 | 响应式布局，适配手机和电脑端 |
| 验证码 | 自定义滑块验证 | 前端滑动组件 + 后端token校验 |

## 三、核心技术点详解

### 3.1 Flask框架与路由

**技术点**：Flask是一个轻量级的Python Web框架，通过装饰器定义路由。

**作用**：
- 将URL映射到Python函数，处理HTTP请求（GET/POST）
- 支持蓝图（Blueprint）组织代码，实现模块化
- 提供模板渲染、文件上传、静态文件服务等功能

**不用会怎样**：
- 需要手动处理HTTP请求解析和响应生成
- 代码结构混乱，难以维护
- 无法方便地集成数据库、认证等功能

**关键概念**：
- `@app.route('/url')`：路由装饰器
- `request`：请求对象，获取表单数据、文件等
- `render_template()`：渲染Jinja2模板
- `redirect()`：重定向到其他URL
- `Blueprint`：蓝图，模块化组织路由

---

### 3.2 Jinja2模板与响应式布局

**技术点**：Jinja2是Flask默认的模板引擎，支持模板继承、变量替换、条件判断等。

**作用**：
- 将Python变量注入HTML模板，实现动态页面
- 通过模板继承复用页面结构（头部、导航、底部）
- 使用Bootstrap 5实现响应式布局，适配不同屏幕尺寸

**不用会怎样**：
- 需要手动拼接HTML字符串，容易出错
- 页面结构重复，难以维护
- 无法适配手机端访问

**响应式布局关键点**：

```html
<!-- viewport设置 -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<!-- Bootstrap栅格系统 -->
<div class="container">
    <div class="row">
        <div class="col-md-6 col-sm-12">
            <!-- 中等屏幕6列，小屏幕12列 -->
        </div>
    </div>
</div>

<!-- 媒体查询 -->
@media (max-width: 768px) {
    /* 手机端样式 */
}
```

---

### 3.3 Flask-SQLAlchemy数据库模型

**技术点**：Flask-SQLAlchemy是SQLAlchemy的Flask扩展，提供对象关系映射。

**作用**：
- 将Python类映射到数据库表
- 提供ORM操作（增删改查），无需编写SQL语句
- 支持数据库迁移和事务管理

**不用会怎样**：
- 需要手动编写SQL语句，容易出错
- 数据库操作与业务逻辑耦合，难以维护
- 无法利用ORM的安全特性（如防SQL注入）

**核心模型设计**：

| 模型 | 字段 | 类型 | 说明 |
|------|------|------|------|
| User | id | Integer | 主键 |
| | username | String | 用户名（唯一） |
| | password_hash | String | 密码哈希值 |
| | role | String | 角色（admin/farmer） |
| | phone | String | 手机号 |
| | email | String | 邮箱 |
| | created_at | DateTime | 创建时间 |
| Detection | id | Integer | 主键 |
| | user_id | Integer | 外键，关联用户 |
| | image_path | String | 上传图片路径 |
| | leaf_area | Float | 叶片面积 |
| | lesion_area | Float | 病斑面积 |
| | lesion_ratio | Float | 病斑占比 |
| | result_image | String | 结果图片路径 |
| | status | String | 检测状态 |
| | created_at | DateTime | 创建时间 |

---

### 3.4 Flask-Login认证与角色权限控制

**技术点**：Flask-Login管理用户登录状态，提供装饰器保护路由。

**作用**：
- 管理用户会话（session）
- 提供`@login_required`装饰器保护需要登录的路由
- 支持角色权限控制（管理员/农户）

**不用会怎样**：
- 需要手动管理用户会话和登录状态
- 路由无法自动校验登录状态
- 无法区分不同角色的访问权限

**关键配置**：

```python
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # 未登录时重定向的页面

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 登录保护装饰器
@login_required
def protected_route():
    pass

# 角色权限装饰器
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role != role:
                abort(403)  # 无权限
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

---

### 3.5 Werkzeug密码哈希

**技术点**：Werkzeug提供安全的密码哈希函数。

**作用**：
- 将用户密码进行哈希处理后存储，不存储明文密码
- 验证登录时比对哈希值，而非明文密码

**不用会怎样**：
- 数据库泄露时用户密码直接暴露
- 违反安全规范，存在严重安全隐患

**使用方法**：

```python
from werkzeug.security import generate_password_hash, check_password_hash

# 注册时生成密码哈希
password_hash = generate_password_hash(password, method='pbkdf2:sha256')

# 登录时验证密码
if check_password_hash(user.password_hash, password):
    # 密码正确
    pass
```

---

### 3.6 CSRF防护（Flask-WTF）

**技术点**：Flask-WTF提供表单处理和CSRF（跨站请求伪造）防护。

**作用**：
- 生成和验证CSRF token，防止跨站请求伪造攻击
- 提供表单验证功能，确保用户输入符合要求

**不用会怎样**：
- 网站容易受到CSRF攻击，导致用户在不知情的情况下执行恶意操作
- 无法验证表单数据的合法性

**使用方法**：

```html
<!-- 表单中添加CSRF token -->
<form method="POST">
    {{ form.hidden_tag() }}  <!-- 自动添加CSRF token -->
    {{ form.username() }}
    {{ form.password() }}
    <button type="submit">登录</button>
</form>
```

---

### 3.7 文件上传

**技术点**：Flask提供文件上传功能，配合secure_filename处理文件名。

**作用**：
- 接收用户上传的叶片图片
- 安全处理文件名，防止路径遍历攻击
- 限制文件大小和类型

**不用会怎样**：
- 用户可能上传恶意文件或超大文件
- 文件名可能包含路径遍历字符（如`../../etc/passwd`）

**安全配置**：

```python
# 配置文件上传
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB限制

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 处理文件上传
file = request.files['file']
if file and allowed_file(file.filename):
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
```

---

### 3.8 滑块验证码

**技术点**：自定义滑块验证组件，前端滑动+后端token校验。

**作用**：
- 防止自动化脚本批量注册或暴力破解登录
- 区分人类用户和机器人

**不用会怎样**：
- 网站容易受到自动化攻击
- 可能导致账号被暴力破解或垃圾注册

**实现原理**：

```
┌─────────────────────────────────────┐
│  前端流程                              │
├─────────────────────────────────────┤
│  1. 加载页面时请求验证码背景图和滑块    │
│  2. 用户拖动滑块完成验证                │
│  3. 计算滑动距离，生成验证token         │
│  4. 将token发送到后端校验              │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  后端流程                              │
├─────────────────────────────────────┤
│  1. 生成验证码背景图和滑块位置          │
│  2. 将正确位置存储到session中          │
│  3. 接收前端token，验证滑动距离是否正确 │
│  4. 返回验证结果                      │
└─────────────────────────────────────┘
```

**前端组件**：

```html
<div class="captcha-container">
    <div class="captcha-bg">
        <!-- 验证码背景图 -->
        <div class="captcha-slider" id="slider">
            <!-- 滑块 -->
        </div>
    </div>
    <div class="captcha-tips">请拖动滑块完成验证</div>
</div>
```

---

### 3.9 后端病斑检测API集成

**技术点**：将现有的病斑检测代码封装为API接口。

**作用**：
- 提供HTTP接口供前端调用
- 接收上传的图片，返回检测结果
- 支持同步和异步检测模式

**不用会怎样**：
- 前端无法调用检测功能
- 检测逻辑与前端耦合，难以维护

**API设计**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/detect` | POST | 上传图片并检测病斑 |
| `/api/detect/<id>` | GET | 查询检测结果 |
| `/api/detect/<id>` | DELETE | 删除检测记录 |
| `/api/user/detections` | GET | 查询当前用户的检测记录 |

---

## 四、项目目录结构

```
car_project/
├── app/                          # Flask应用目录
│   ├── __init__.py               # 应用工厂函数
│   ├── config.py                 # 配置文件
│   ├── extensions.py             # 扩展初始化（db, login_manager等）
│   ├── models.py                 # 数据库模型（User, Detection）
│   ├── utils.py                  # 工具函数（验证码生成、文件处理等）
│   ├── blueprints/               # 蓝图目录
│   │   ├── auth.py               # 认证蓝图（注册、登录、验证码）
│   │   ├── farmer.py             # 农户蓝图（上传检测、查看结果）
│   │   └── admin.py              # 管理员蓝图（用户管理、统计）
│   ├── templates/                # 模板目录
│   │   ├── base.html             # 基础模板
│   │   ├── auth/                 # 认证页面
│   │   │   ├── login.html        # 登录页面
│   │   │   └── register.html     # 注册页面
│   │   ├── farmer/               # 农户页面
│   │   │   ├── index.html        # 农户首页
│   │   │   ├── upload.html       # 上传检测页面
│   │   │   └── result.html       # 检测结果页面
│   │   └── admin/                # 管理员页面
│   │       ├── index.html        # 管理员首页
│   │       ├── users.html        # 用户管理页面
│   │       └── stats.html        # 统计页面
│   └── static/                   # 静态文件目录
│       ├── css/                  # 样式文件
│       │   └── main.css          # 自定义样式
│       ├── js/                   # JavaScript文件
│       │   ├── captcha.js        # 滑块验证码逻辑
│       │   └── upload.js         # 文件上传逻辑
│       └── images/               # 图片资源
├── uploads/                      # 上传文件存储目录
├── src/                          # 原有检测代码目录
│   ├── lesion_detection.py       # 颜色阈值检测
│   ├── inference_sam.py          # SAM检测
│   └── ...                       # 其他检测代码
├── output/                       # 检测结果输出目录
├── models/                       # 模型权重目录
├── venv/                         # Python虚拟环境
├── doc/                          # 文档目录
├── run.py                        # 应用启动入口
└── requirements.txt              # 依赖清单
```

---

## 五、端点枚举表

### 5.1 认证模块（auth蓝图）

| URL | 方法 | 蓝图 | 模板 | 权限 | 说明 |
|-----|------|------|------|------|------|
| `/login` | GET/POST | auth | auth/login.html | 匿名 | 用户登录 |
| `/register` | GET/POST | auth | auth/register.html | 匿名 | 用户注册 |
| `/logout` | GET | auth | - | 登录用户 | 退出登录 |
| `/captcha` | GET | auth | - | 匿名 | 获取验证码图片 |
| `/captcha/verify` | POST | auth | - | 匿名 | 验证滑块位置 |

### 5.2 农户模块（farmer蓝图）

| URL | 方法 | 蓝图 | 模板 | 权限 | 说明 |
|-----|------|------|------|------|------|
| `/farmer/` | GET | farmer | farmer/index.html | farmer | 农户首页 |
| `/farmer/upload` | GET/POST | farmer | farmer/upload.html | farmer | 上传检测图片 |
| `/farmer/result/<id>` | GET | farmer | farmer/result.html | farmer | 查看检测结果 |
| `/farmer/detections` | GET | farmer | farmer/index.html | farmer | 检测记录列表 |

### 5.3 管理员模块（admin蓝图）

| URL | 方法 | 蓝图 | 模板 | 权限 | 说明 |
|-----|------|------|------|------|------|
| `/admin/` | GET | admin | admin/index.html | admin | 管理员首页 |
| `/admin/users` | GET | admin | admin/users.html | admin | 用户列表 |
| `/admin/users/add` | GET/POST | admin | admin/user_edit.html | admin | 添加用户 |
| `/admin/users/edit/<id>` | GET/POST | admin | admin/user_edit.html | admin | 编辑用户 |
| `/admin/users/delete/<id>` | POST | admin | - | admin | 删除用户 |
| `/admin/stats` | GET | admin | admin/stats.html | admin | 检测统计 |

### 5.4 API接口

| URL | 方法 | 说明 | 权限 |
|-----|------|------|------|
| `/api/detect` | POST | 上传图片并检测 | farmer |
| `/api/detect/<id>` | GET | 查询检测结果 | farmer/admin |
| `/api/detect/<id>` | DELETE | 删除检测记录 | farmer/admin |
| `/api/user/detections` | GET | 当前用户检测记录 | farmer |
| `/api/admin/users` | GET | 获取所有用户 | admin |
| `/api/admin/users/<id>` | PUT | 更新用户信息 | admin |
| `/api/admin/users/<id>` | DELETE | 删除用户 | admin |

---

## 六、数据库表结构

### 6.1 users表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 用户ID |
| username | VARCHAR(50) | UNIQUE NOT NULL | 用户名 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希 |
| role | VARCHAR(20) | NOT NULL DEFAULT 'farmer' | 角色（admin/farmer） |
| phone | VARCHAR(20) | - | 手机号 |
| email | VARCHAR(100) | - | 邮箱 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否激活 |

### 6.2 detections表

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 检测ID |
| user_id | INTEGER | FOREIGN KEY REFERENCES users(id) | 用户ID |
| image_path | VARCHAR(255) | NOT NULL | 上传图片路径 |
| leaf_area | FLOAT | - | 叶片面积（像素） |
| lesion_area | FLOAT | - | 病斑面积（像素） |
| lesion_ratio | FLOAT | - | 病斑占比（%） |
| result_image | VARCHAR(255) | - | 结果图片路径 |
| status | VARCHAR(20) | DEFAULT 'processing' | 状态（processing/done/failed） |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

---

## 七、关键流程图

### 7.1 用户注册流程

```
用户访问注册页面 → 填写表单（用户名、密码、手机号）→ 获取验证码 → 拖动滑块验证
    ↓
后端验证验证码 → 检查用户名是否已存在 → 生成密码哈希 → 保存用户到数据库 → 重定向到登录页面
```

### 7.2 用户登录流程

```
用户访问登录页面 → 填写用户名和密码 → 拖动滑块验证
    ↓
后端验证验证码 → 查询用户 → 验证密码哈希 → 创建用户会话 → 重定向到首页
    ↓
根据用户角色重定向到对应页面（农户首页/管理员首页）
```

### 7.3 病斑检测流程

```
农户上传图片 → 前端验证文件类型和大小 → 发送到后端
    ↓
后端保存文件 → 调用检测模块（SAM或颜色阈值）→ 获取检测结果
    ↓
保存检测记录到数据库 → 返回结果给前端 → 显示检测报告和防治方案
```

### 7.4 管理员管理用户流程

```
管理员登录 → 进入用户管理页面 → 查看用户列表
    ↓
选择操作（添加/编辑/删除用户） → 提交表单 → 更新数据库 → 刷新列表
```

---

## 八、安全注意事项

| 安全风险 | 防护措施 |
|----------|----------|
| 密码泄露 | 使用Werkzeug密码哈希，不存储明文 |
| SQL注入 | 使用Flask-SQLAlchemy ORM，参数化查询 |
| CSRF攻击 | 使用Flask-WTF生成CSRF token |
| 文件上传漏洞 | 检查文件类型、限制文件大小、使用secure_filename |
| 暴力破解 | 滑块验证码、登录失败次数限制 |
| XSS攻击 | Jinja2自动转义HTML、验证用户输入 |
| 路径遍历 | 使用secure_filename处理文件名 |

---

## 九、部署方案

### 9.1 开发环境

```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python run.py init

# 启动开发服务器
python run.py run
```

### 9.2 生产环境

**推荐使用Gunicorn + Nginx**：

```bash
# 安装Gunicorn
pip install gunicorn

# 使用Gunicorn启动
gunicorn -w 4 -b 0.0.0.0:5000 app:create_app()

# Nginx配置示例
server {
    listen 80;
    server_name your_domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        root /path/to/project;
        expires 30d;
    }
    
    location /uploads/ {
        root /path/to/project;
        expires 30d;
    }
}
```

---

## 十、后续扩展

1. **防治方案推荐**：根据病斑类型和严重程度，推荐相应的防治方案
2. **批量上传**：支持一次性上传多张图片进行检测
3. **检测历史分析**：展示用户的检测历史趋势
4. **数据统计图表**：管理员查看检测统计数据
5. **移动端优化**：专门针对手机端优化的UI和交互
6. **邮件通知**：检测完成后发送邮件通知用户
7. **多语言支持**：支持中英文切换