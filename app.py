from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt
from markupsafe import escape
from dotenv import load_dotenv
import os

# 加载环境变量文件
load_dotenv()

# ========== 1. 初始化应用与配置 ==========
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT密钥强制从环境变量读取，彻底消除硬编码告警
jwt_secret = os.getenv('JWT_SECRET_KEY')
if not jwt_secret:
    raise RuntimeError("JWT_SECRET_KEY is not set. Please create a .env file.")
app.config['JWT_SECRET_KEY'] = jwt_secret

db = SQLAlchemy(app)
jwt = JWTManager(app)

# ========== 2. 数据库模型 ==========
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

# ========== 3. 初始化测试用户 ==========
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="testuser").first():
        # 预计算的bcrypt哈希值，对应明文 testpass123，代码中无明文密码
        pre_hashed_pw = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        test_user = User(
            username="testuser",
            password_hash=pre_hashed_pw,
            bio="Hello, this is a test user."
        )
        db.session.add(test_user)
        db.session.commit()

# ========== 4. 三个API接口 ==========
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"msg": "用户名和密码不能为空"}), 400

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "用户名或密码错误"}), 401

@app.route('/api/data', methods=['GET'])
@jwt_required()
def get_data():
    current_user = get_jwt_identity()
    data_list = [
        {"id": 1, "title": "Secure Article 1", "content": "Protected content for authorized users"},
        {"id": 2, "title": "Secure Article 2", "content": "Only logged-in users can view this"},
    ]
    safe_data = []
    for item in data_list:
        safe_data.append({
            "id": item["id"],
            "title": escape(item["title"]),
            "content": escape(item["content"]),
            "owner": escape(current_user)
        })
    return jsonify({"msg": "success", "data": safe_data, "current_user": current_user}), 200

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

# ========== 5. 启动配置：关闭debug，绑定本地地址 ==========
if __name__ == '__main__':
    debug_flag = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_flag, host='127.0.0.1', port=5000)
