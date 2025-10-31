import os
import time
import logging
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from faster_whisper import WhisperModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import database

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this")

CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000"])
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'images')

# Google OAuth Config
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# OpenAI Client
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    logging.info("Khởi tạo OpenAI client thành công.")
except Exception as e:
    logging.error(f"Lỗi khi khởi tạo OpenAI client: {e}")
    client = None

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Whisper Model
# Tự động tải mô hình từ Hugging Face Hub (nếu chưa có)
MODEL_PATH = "Duke03/Whisper-medium-vi-ct2-int8" 
logging.info(f"Bắt đầu tải mô hình Whisper từ: {MODEL_PATH}")
try:
    whisper_model = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8", local_files_only=False)
    logging.info("Tải mô hình Whisper thành công.")
except Exception as e:
    logging.error(f"Lỗi khi tải mô hình Whisper: {e}")
    whisper_model = None

SYSTEM_PROMPT = """
Bạn là một trợ lý AI lập trình tên là CodeMate. Nhiệm vụ của bạn là cung cấp các câu trả lời hữu ích, rõ ràng và có cấu trúc cho các câu hỏi của người dùng, chủ yếu liên quan đến lập trình, công nghệ và khoa học máy tính.

QUY TẮC ĐỊNH DẠNG PHẢN HỒI:
- Sử dụng Markdown để định dạng câu trả lời của bạn.
- Dùng tiêu đề (`##`) cho các phần chính.
- Dùng danh sách có dấu đầu dòng (`-`) hoặc danh sách được đánh số (`1.`) để liệt kê các mục.
- Nhấn mạnh các thuật ngữ quan trọng bằng cách in **đậm** hoặc *nghiêng*.
- Đối với các đoạn mã, hãy sử dụng khối mã được rào chắn với tên ngôn ngữ rõ ràng (ví dụ: ```python... ```).
- Giữ cho các đoạn văn ngắn gọn và đi thẳng vào vấn đề.
- Luôn trả lời bằng tiếng Việt.
"""

# ==================== MIDDLEWARE ====================

def login_required(f):
    """Decorator để kiểm tra đăng nhập"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized", "message": "Vui lòng đăng nhập"}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROUTES - FRONTEND ====================

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(FRONTEND_DIR, path)
    except:
        return jsonify({"error": "File not found"}), 404

@app.route('/CodeMate_AI.png')
def serve_favicon():
    try:
        return send_from_directory(IMAGE_DIR, 'CodeMate_AI.png', mimetype='image/png')
    except FileNotFoundError:
        logging.error(f"Không tìm thấy file favicon: {os.path.join(IMAGE_DIR, 'CodeMate_AI.png')}")
        return jsonify({"error": "Favicon not found"}), 404

# ==================== ROUTES - AUTH ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Đăng ký tài khoản mới"""
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name', email.split('@')[0])
    
    if not email or not password:
        return jsonify({"error": "Email và password là bắt buộc"}), 400
    
    user_id = database.create_user(email, password, full_name)
    
    if user_id:
        return jsonify({"message": "Đăng ký thành công", "user_id": user_id}), 201
    else:
        return jsonify({"error": "Email đã tồn tại hoặc lỗi hệ thống"}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Đăng nhập với email/password"""
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email và password là bắt buộc"}), 400
    
    user = database.verify_user(email, password)
    
    if user:
        session['user_id'] = user['id']
        session['email'] = user['email']
        
        return jsonify({
            "message": "Đăng nhập thành công",
            "user": {
                "id": user['id'],
                "email": user['email'],
                "full_name": user['full_name'],
                "avatar_url": user.get('avatar_url')
            }
        }), 200
    else:
        return jsonify({"error": "Email hoặc mật khẩu không đúng"}), 401

@app.route('/api/auth/google', methods=['POST'])
def google_login():
    """Đăng nhập với Google OAuth"""
    data = request.get_json()
    token = data.get('credential')
    
    if not token:
        return jsonify({"error": "Token không hợp lệ"}), 400
    
    try:
        # Xác thực token từ Google
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        google_id = idinfo['sub']
        email = idinfo['email']
        full_name = idinfo.get('name', email.split('@')[0])
        avatar_url = idinfo.get('picture')
        
        # Tạo hoặc lấy user
        user = database.get_or_create_google_user(google_id, email, full_name, avatar_url)
        
        if user:
            session['user_id'] = user['id']
            session['email'] = user['email']
            
            return jsonify({
                "message": "Đăng nhập Google thành công",
                "user": {
                    "id": user['id'],
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "avatar_url": user.get('avatar_url')
                }
            }), 200
        else:
            return jsonify({"error": "Lỗi khi xử lý đăng nhập Google"}), 500
            
    except ValueError as e:
        logging.error(f"Lỗi xác thực Google token: {e}")
        return jsonify({"error": "Token không hợp lệ"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Đăng xuất"""
    session.clear()
    return jsonify({"message": "Đăng xuất thành công"}), 200

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """Lấy thông tin user hiện tại"""
    user_id = session.get('user_id')
    user = database.get_user_by_id(user_id)
    
    if user:
        return jsonify({
            "id": user['id'],
            "email": user['email'],
            "full_name": user['full_name'],
            "avatar_url": user.get('avatar_url')
        }), 200
    else:
        return jsonify({"error": "User không tồn tại"}), 404

# ==================== ROUTES - CONVERSATIONS ====================

@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Lấy danh sách conversations của user"""
    user_id = session.get('user_id')
    conversations = database.get_user_conversations(user_id)
    return jsonify(conversations), 200

@app.route('/api/conversations', methods=['POST'])
@login_required
def create_new_conversation():
    """Tạo conversation mới"""
    user_id = session.get('user_id')
    data = request.get_json()
    title = data.get('title', 'Cuộc hội thoại mới')
    
    conversation_id = database.create_conversation(user_id, title)
    
    if conversation_id:
        return jsonify({"conversation_id": conversation_id, "title": title}), 201
    else:
        return jsonify({"error": "Lỗi khi tạo conversation"}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    """Lấy messages của một conversation"""
    messages = database.get_conversation_messages(conversation_id)
    return jsonify(messages), 200

@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation_route(conversation_id):
    """Xóa conversation"""
    user_id = session.get('user_id')
    success = database.delete_conversation(conversation_id, user_id)
    
    if success:
        return jsonify({"message": "Xóa thành công"}), 200
    else:
        return jsonify({"error": "Không thể xóa conversation"}), 400

@app.route('/api/conversations/<int:conversation_id>/title', methods=['PUT'])
@login_required
def update_conversation_title_route(conversation_id):
    """Cập nhật tiêu đề conversation"""
    data = request.get_json()
    title = data.get('title')
    
    if not title:
        return jsonify({"error": "Title không được để trống"}), 400
    
    success = database.update_conversation_title(conversation_id, title)
    
    if success:
        return jsonify({"message": "Cập nhật thành công"}), 200
    else:
        return jsonify({"error": "Lỗi khi cập nhật title"}), 500

# ==================== ROUTES - CHAT ====================

@app.route('/api/chat', methods=['POST'])
@login_required
def handle_chat():
    """Endpoint xử lý chat"""
    user_id = session.get('user_id')
    conversation_id = request.form.get('conversation_id') or request.args.get('conversation_id')
    
    if not conversation_id:
        return jsonify({"error": "conversation_id là bắt buộc"}), 400
    
    conversation_id = int(conversation_id)
    user_input = ""
    temp_path = None
    
    # Xử lý đầu vào
    if 'audioFile' in request.files:
        audio_file = request.files['audioFile']
        if audio_file.filename == '':
            return jsonify({"error": "Tệp không có tên"}), 400
        
        temp_dir = "temp_audio"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{int(time.time())}_{audio_file.filename}")
        audio_file.save(temp_path)
        logging.info(f"Đã nhận tệp âm thanh: {temp_path}")
        
        if not whisper_model:
            return jsonify({"error": "Mô hình Whisper không khả dụng"}), 500
        
        try:
            logging.info("Bắt đầu phiên mã...")
            start_time = time.time()
            segments, _ = whisper_model.transcribe(temp_path, beam_size=5, language="vi")
            user_input = "".join(segment.text for segment in segments).strip()
            processing_time = time.time() - start_time
            logging.info(f"Phiên mã thành công sau {processing_time:.2f}s: '{user_input}'")
        except Exception as e:
            logging.error(f"Lỗi khi phiên mã: {e}")
            return jsonify({"error": "Lỗi xử lý âm thanh"}), 500
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
    
    elif 'text' in request.form:
        user_input = request.form['text']
        logging.info(f"Đã nhận yêu cầu văn bản: '{user_input}'")
    else:
        return jsonify({"error": "Yêu cầu phải chứa 'audioFile' hoặc 'text'"}), 400
    
    if not user_input:
        return jsonify({"error": "Đầu vào rỗng sau khi xử lý"}), 400
    
    # Gọi OpenAI
    if not client:
        return jsonify({"error": "OpenAI client không khả dụng"}), 500
    
    try:
        logging.info("Gửi yêu cầu đến OpenAI...")
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ]
        )
        ai_response = completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Lỗi khi gọi OpenAI API: {e}")
        return jsonify({"error": "Lỗi kết nối đến AI service"}), 500
    
    # Lưu messages vào database
    database.save_message(conversation_id, 'user', user_input)
    database.save_message(conversation_id, 'assistant', ai_response)
    
    return jsonify({
        "user_input": user_input,
        "ai_response": ai_response
    })

# ==================== RUN SERVER ====================

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)