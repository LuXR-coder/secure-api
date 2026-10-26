from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt
from markupsafe import escape

# ========== 1. 初始化应用与配置 ==========
app = Flask(__name__)
# 配置SQLite数据库，文件存在本地instance目录
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# JWT密钥（学习用，生产环境必须存在环境变量里）
app.config['JWT_SECRET_KEY'] = 'your-study-secret-key-2024'

# 初始化ORM和JWT管理器
db = SQLAlchemy(app)
jwt = JWTManager(app)

# ========== 2. 定义数据库模型 ==========
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.String(200), default="")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "bio": self.bio
        }

# ========== 3. 初始化数据库与测试用户 ==========
with app.app_context():
    db.create_all()
    # 避免重复创建测试用户
    if not User.query.filter_by(username="testuser").first():
        # 密码用bcrypt哈希，永不存储明文
        password = "testpass123"
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        test_user = User(
            username="testuser",
            password_hash=hashed_pw.decode('utf-8'),
            bio="Hello, this is a test user."
        )
        db.session.add(test_user)
        db.session.commit()
        print("测试用户创建成功：用户名 testuser，密码 testpass123")

# ========== 4. 三个API接口 ==========
# 接口1：用户登录，返回JWT令牌
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"msg": "用户名和密码不能为空"}), 400

    # ORM参数化查询，防SQL注入
    user = User.query.filter_by(username=username).first()

    # 验证密码哈希
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "用户名或密码错误"}), 401

# 接口2：受保护接口，返回数据列表
@app.route('/api/data', methods=['GET'])
@jwt_required()  # 装饰器自动校验JWT，无有效令牌直接返回401
def get_data():
    current_user = get_jwt_identity()
    
    # 模拟业务数据
    data_list = [
        {"id": 1, "title": "Secure Article 1", "content": "Protected content for authorized users"},
        {"id": 2, "title": "Secure Article 2", "content": "Only logged-in users can view this"},
    ]
    
    # 所有输出做HTML转义，防XSS
    safe_data = []
    for item in data_list:
        safe_data.append({
            "id": item["id"],
            "title": escape(item["title"]),
            "content": escape(item["content"]),
            "owner": escape(current_user)
        })
    
    return jsonify({
        "msg": "success",
        "data": safe_data,
        "current_user": current_user
    }), 200

# 接口3：更新当前用户简介（自定义接口）
@app.route('/api/user/profile', methods=['POST'])
@jwt_required()
def update_profile():
    current_user = get_jwt_identity()
    data = request.get_json()
    new_bio = data.get('bio', '')

    user = User.query.filter_by(username=current_user).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404

    user.bio = new_bio
    db.session.commit()

    return jsonify({
        "msg": "Profile updated",
        "user": {
            "username": escape(user.username),
            "bio": escape(user.bio)
        }
    }), 200

# ========== 5. 启动应用 ==========
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
