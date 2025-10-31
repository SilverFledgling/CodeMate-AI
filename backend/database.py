import os
import mysql.connector
from mysql.connector import pooling
import logging
from dotenv import load_dotenv
import bcrypt

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tạo connection pool
try:
    db_config = {
        "pool_name": "codemate_pool",
        "pool_size": 5,
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "codemate_db")
    }
    
    unix_socket = os.getenv("DB_SOCKET")
    if unix_socket:
        db_config["unix_socket"] = unix_socket
    
    db_pool = pooling.MySQLConnectionPool(**db_config)
    logging.info("Khởi tạo MySQL connection pool thành công.")
except mysql.connector.Error as err:
    logging.error(f"Lỗi khi khởi tạo connection pool: {err}")
    db_pool = None

def get_connection():
    """Lấy connection từ pool"""
    if not db_pool:
        raise Exception("Connection pool không khả dụng")
    return db_pool.get_connection()

# ==================== USER MANAGEMENT ====================

def create_user(email, password, full_name, auth_provider='local', google_id=None):
    """Tạo user mới"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        password_hash = None
        if password:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        query = """
            INSERT INTO users (email, password_hash, full_name, auth_provider, google_id)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (email, password_hash, full_name, auth_provider, google_id))
        conn.commit()
        
        user_id = cursor.lastrowid
        logging.info(f"Tạo user thành công: {email}")
        return user_id
    except mysql.connector.Error as err:
        logging.error(f"Lỗi tạo user: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def verify_user(email, password):
    """Xác thực user với email và password"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM users WHERE email = %s AND auth_provider = 'local'"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        
        if user and user['password_hash']:
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                logging.info(f"Đăng nhập thành công: {email}")
                return user
        
        return None
    except mysql.connector.Error as err:
        logging.error(f"Lỗi xác thực user: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_or_create_google_user(google_id, email, full_name, avatar_url):
    """Lấy hoặc tạo user từ Google OAuth"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Tìm user theo google_id
        query = "SELECT * FROM users WHERE google_id = %s"
        cursor.execute(query, (google_id,))
        user = cursor.fetchone()
        
        if user:
            # Cập nhật thông tin
            update_query = """
                UPDATE users 
                SET full_name = %s, avatar_url = %s, last_login = CURRENT_TIMESTAMP
                WHERE google_id = %s
            """
            cursor.execute(update_query, (full_name, avatar_url, google_id))
            conn.commit()
            logging.info(f"Cập nhật user Google: {email}")
            return user
        else:
            # Tạo user mới
            insert_query = """
                INSERT INTO users (email, full_name, avatar_url, auth_provider, google_id)
                VALUES (%s, %s, %s, 'google', %s)
            """
            cursor.execute(insert_query, (email, full_name, avatar_url, google_id))
            conn.commit()
            
            user_id = cursor.lastrowid
            logging.info(f"Tạo user Google mới: {email}")
            
            # Lấy thông tin user vừa tạo
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
    except mysql.connector.Error as err:
        logging.error(f"Lỗi xử lý Google user: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_user_by_id(user_id):
    """Lấy thông tin user theo ID"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        logging.error(f"Lỗi lấy user: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ==================== CONVERSATION MANAGEMENT ====================

def create_conversation(user_id, title="Cuộc hội thoại mới"):
    """Tạo cuộc hội thoại mới"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "INSERT INTO conversations (user_id, title) VALUES (%s, %s)"
        cursor.execute(query, (user_id, title))
        conn.commit()
        
        conversation_id = cursor.lastrowid
        logging.info(f"Tạo conversation {conversation_id} cho user {user_id}")
        return conversation_id
    except mysql.connector.Error as err:
        logging.error(f"Lỗi tạo conversation: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_user_conversations(user_id):
    """Lấy danh sách conversations của user"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT content FROM messages
                    WHERE conversation_id = c.id AND role = 'user'
                    ORDER BY created_at ASC LIMIT 1) as first_message
            FROM conversations c
            WHERE c.user_id = %s
            ORDER BY c.updated_at DESC
        """
        cursor.execute(query, (user_id,))
        conversations = cursor.fetchall()
        
        logging.info(f"Lấy {len(conversations)} conversations cho user {user_id}")
        return conversations
    except mysql.connector.Error as err:
        logging.error(f"Lỗi lấy conversations: {err}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_conversation_messages(conversation_id):
    """Lấy tất cả messages trong conversation"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT id, role, content, created_at
            FROM messages
            
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """
        cursor.execute(query, (conversation_id,))
        messages = cursor.fetchall()
        
        logging.info(f"Lấy {len(messages)} messages từ conversation {conversation_id}")
        return messages
    except mysql.connector.Error as err:
        logging.error(f"Lỗi lấy messages: {err}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def save_message(conversation_id, role, content):
    """Lưu message vào conversation"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)"
        cursor.execute(query, (conversation_id, role, content))
        conn.commit()
        
        # Cập nhật updated_at của conversation
        update_query = "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        cursor.execute(update_query, (conversation_id,))
        conn.commit()
        
        logging.info(f"Lưu message vào conversation {conversation_id}")
        return cursor.lastrowid
    except mysql.connector.Error as err:
        logging.error(f"Lỗi lưu message: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_conversation_title(conversation_id, title):
    """Cập nhật tiêu đề conversation"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "UPDATE conversations SET title = %s WHERE id = %s"
        cursor.execute(query, (title, conversation_id))
        conn.commit()
        
        logging.info(f"Cập nhật title conversation {conversation_id}")
        return True
    except mysql.connector.Error as err:
        logging.error(f"Lỗi cập nhật title: {err}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def delete_conversation(conversation_id, user_id):
    """Xóa conversation (chỉ cho phép user sở hữu)"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "DELETE FROM conversations WHERE id = %s AND user_id = %s"
        cursor.execute(query, (conversation_id, user_id))
        conn.commit()
        
        logging.info(f"Xóa conversation {conversation_id}")
        return cursor.rowcount > 0
    except mysql.connector.Error as err:
        logging.error(f"Lỗi xóa conversation: {err}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()