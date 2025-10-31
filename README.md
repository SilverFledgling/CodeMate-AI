
# CodeMate AI 🤖

<p align="center">
<img src="images/CodeMate_AI.png" alt="CodeMate AI Logo" width="150"/>
</p>
````markdown
Một ứng dụng web sử dụng mô hình Whisper và OpenAI API để tạo thành một trợ lý AI mạnh mẽ, chuyên hỗ trợ các tác vụ lập trình thông qua giao tiếp bằng giọng nói Tiếng Việt.

## ✨ Tính năng chính

* **Xác thực người dùng:** Đăng nhập/Đăng ký bằng email (local) hoặc tài khoản Google (OAuth 2.0).
* **Giao diện Chat trực quan:** Giao diện chat hiện đại, thân thiện, tương tự như các ứng dụng chat AI phổ biến.
* **Hỗ trợ Markdown:** Phản hồi từ AI được render dưới dạng Markdown, giúp hiển thị code, danh sách, và các định dạng văn bản một cách rõ ràng.
* **Lịch sử cuộc trò chuyện:** Tự động lưu và hiển thị lịch sử các cuộc hội thoại, cho phép người dùng quay lại các cuộc trò chuyện trước đó.
* **Nhận diện giọng nói (Speech-to-Text):** Người dùng có thể nhập liệu bằng giọng nói thông qua micro, sử dụng [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) để chuyển đổi thành văn bản.
* **Backend hiệu suất cao:** Xây dựng trên nền tảng Flask (Python) với connection pool cho MySQL để quản lý kết nối cơ sở dữ liệu hiệu quả.

## 🛠️ Công nghệ sử dụng

| Phân loại | Công nghệ |
| :--- | :--- |
| **Backend** | Python, Flask, Gunicorn (cho production) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Cơ sở dữ liệu** | MySQL |
| **AI & NLP** | OpenAI API (GPT-4o), Faster-Whisper (Speech-to-Text) |
| **Xác thực** | Google OAuth 2.0, Bcrypt (cho mật khẩu local) |

## 📋 Yêu cầu cài đặt

Trước khi bắt đầu, hãy đảm bảo bạn đã cài đặt các công cụ sau trên máy của mình:

* [Python 3.9+](https://www.python.org/)
* Cài đặt MySQL Server (ví dụ: từ [trang chủ MySQL](https://dev.mysql.com/downloads/mysql/))
* (Khuyên dùng cho Whisper) [ffmpeg](https://ffmpeg.org/download.html)

## ⚙️ Cài đặt và Chạy dự án

### 1. Clone dự án

```bash
git clone [https://github.com/SilverFledgling/CodeMate-AI.git](https://github.com/SilverFledgling/CodeMate-AI.git)
cd CodeMate-AI
````

### 2\. Cài đặt Backend (Python)

Di chuyển vào thư mục `backend`, tạo một môi trường ảo và cài đặt các thư viện cần thiết.

```bash
cd backend

# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows:
venv\Scripts\activate
# Trên macOS/Linux:
source venv/bin/activate

# Cài đặt các thư viện từ requirements.txt
pip install -r requirements.txt
```

### 3\. Cài đặt Cơ sở dữ liệu (MySQL)

1.  Mở trình quản lý MySQL của bạn (ví dụ: MySQL Workbench, DBeaver, hoặc command line).
2.  Tạo một database mới (tên mặc định trong file `.env` là `codemate_db`).
    ```sql
    CREATE DATABASE codemate_db;
    ```
3.  Sử dụng database vừa tạo và chạy file `database.sql` (nằm ở thư mục gốc) để khởi tạo các bảng (users, conversations, messages).
    ```bash
    # Từ terminal (chạy ở thư mục gốc)
    mysql -u [ten_user] -p codemate_db < database.sql
    ```

### 4\. Cấu hình Biến môi trường

Đây là bước quan trọng nhất. Tạo một file tên là `.env` trong thư mục `backend/` (cùng cấp với `nlp_main.py`).

**Nội dung file `.env`:**

> **Cảnh báo bảo mật:** KHÔNG BAO GIỜ chia sẻ file `.env` thật của bạn. Sử dụng file này làm mẫu và thay thế bằng các giá trị của bạn.

```ini
# API Key của OpenAI
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY_HERE

# Cấu hình cơ sở dữ liệu MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=codemate_db

# Khóa bí mật của Flask để quản lý session
SECRET_KEY=YOUR_VERY_STRONG_RANDOM_SECRET_KEY

# Client ID của Google (lấy từ Google Cloud Console)
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com
```

### 5\. Chạy ứng dụng

Sau khi hoàn tất các bước trên, bạn có thể khởi chạy server Flask (đảm bảo bạn đang ở trong thư mục `backend/` và môi trường ảo `venv` đã được kích hoạt):

```bash
# Chế độ phát triển (development)
flask run

# Hoặc chạy trực tiếp file
python nlp_main.py
```

Ứng dụng sẽ chạy tại `http://localhost:5000`. Bạn có thể truy cập `http://localhost:5000/login.html` để bắt đầu.

-----

## 🌳 Cấu trúc thư mục

Dưới đây là cấu trúc thư mục của dự án, giúp dễ dàng quản lý:

```
/CodeMate-AI
|
|-- /backend
|   |-- nlp_main.py       # Flask App chính, API routes, Google Auth
|   |-- database.py       # Module quản lý kết nối và truy vấn DB
|   |-- requirements.txt  # Danh sách thư viện Python
|   |-- .env              # (Bí mật) File chứa các khóa API và cấu hình
|
|-- /frontend
|   |-- index.html        # Giao diện chat chính
|   |-- login.html        # Trang đăng nhập/đăng ký
|   |-- script.js         # Logic JavaScript phía client
|   |-- style.css         # CSS cho giao diện
|   |-- CodeMate_AI.jpg   # Logo
|
|-- database.sql            # Script khởi tạo schema cho MySQL
|-- fine_tuning_on_colab.ipynb # Notebook cho việc fine-tuning (nếu có)
|-- README.md               # Tài liệu hướng dẫn dự án
|-- .gitignore
```

```
```
