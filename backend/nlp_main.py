# --- FILE: backend/nlp_phobert.py (phiên bản cập nhật) ---

import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from transformers import WhisperForConditionalGeneration, WhisperProcessor
import torch
import librosa
import mysql.connector
from mysql.connector import Error
from openai import OpenAI
from dotenv import load_dotenv

# Tải biến môi trường
# Tải các biến môi trường từ file .env
load_dotenv()

# --- CÀI ĐẶT CƠ BẢN ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__,
            template_folder='../frontend',
            static_folder='../frontend',
            static_url_path='')
CORS(app)

# --- KHỞI TẠO OPENAI CLIENT ---
# Lấy API key từ biến môi trường
api_key = os.environ.get("OPENAI_API_KEY")
client = None  # Khởi tạo client là None trước

# Kiểm tra xem API key có tồn tại không
if not api_key:
    logging.error("LỖI: Biến môi trường OPENAI_API_KEY chưa được thiết lập hoặc không đọc được từ file .env.")
else:
    try:
        # Chỉ khởi tạo client nếu có key
        client = OpenAI(api_key=api_key)
        logging.info("OpenAI client đã được khởi tạo thành công.")
    except Exception as e:
        # Bắt các lỗi khác có thể xảy ra khi khởi tạo
        logging.error(f"Lỗi khi khởi tạo OpenAI client: {e}")

# --- CẤU HÌNH DATABASE ---
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "speech_recognition"
}

# --- TẢI MODEL WHISPER ---
logging.info("Bắt đầu tải mô hình Whisper...")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logging.info(f"Sử dụng thiết bị: {DEVICE}")

try:
    whisper_model_path = "Duke03/whisper_medium_finetuned_vi"
    whisper_processor = WhisperProcessor.from_pretrained(whisper_model_path)
    whisper_model = WhisperForConditionalGeneration.from_pretrained(whisper_model_path, low_cpu_mem_usage=True, torch_dtype=torch.bfloat16).to(DEVICE)
    logging.info(f"Đã tải thành công mô hình Whisper từ: {whisper_model_path}")

except Exception as e:
    logging.error(f"LỖI NGHIÊM TRỌNG: Không thể tải mô hình Whisper. Lỗi: {e}", exc_info=True)
    exit()

# --- CÁC HÀM XỬ LÝ ---
def save_to_db(audio_filename, transcript, response):
    """Lưu kết quả vào database."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        # Cột predicted_intent có thể để trống hoặc ghi là "llm_generation"
        query = "INSERT INTO history (audio_filename, transcript, response) VALUES (%s, %s, %s)"
        cursor.execute(query, (audio_filename, transcript, response))
        conn.commit()
    except Error as e:
        logging.error(f"Lỗi khi lưu vào DB: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def recognize_speech_from_file(audio_path):
    try:
        speech_array, _ = librosa.load(audio_path, sr=16000)
        input_features = whisper_processor(speech_array, sampling_rate=16000, return_tensors="pt").input_features.to(DEVICE)
        input_features = input_features.to(whisper_model.dtype)
        predicted_ids = whisper_model.generate(input_features, max_length=256)
        transcript = whisper_processor.batch_decode(predicted_ids, skip_special_tokens=True, normalize=True)[0]
        logging.info(f"Nhận diện thành công: '{transcript}'")
        return transcript.strip()
    except Exception as e:
        logging.error(f"Lỗi khi nhận diện giọng nói: {e}", exc_info=True)
        return None

def generate_response_with_llm(prompt: str) -> str:
    """Gửi yêu cầu đến API của OpenAI để tạo ra phản hồi."""
    if not client:
        return "Lỗi: OpenAI client chưa được khởi tạo. Vui lòng kiểm tra API key trong file .env"
    if not prompt:
        return "Không có nội dung để xử lý."

    try:
        logging.info(f"Đang gửi prompt tới OpenAI: '{prompt}'")
        completion = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý ảo hữu ích, trả lời chính xác, chuẩn xác, súc tích, ngắn gọn, đầy đủ ý, nội dung, và thân thiện bằng tiếng Việt."},
                {"role": "user", "content": prompt}
            ]
        )
        response_text = completion.choices[0].message.content
        logging.info("OpenAI đã tạo phản hồi thành công.")
        return response_text.strip()
    except Exception as e:
        logging.error(f"Lỗi khi gọi API OpenAI: {e}", exc_info=True)
        return "Rất tiếc, đã có lỗi xảy ra trong quá trình tạo phản hồi từ AI."

# --- API ENDPOINTS ---
@app.route('/')
def index():
    return render_template("index.html")

@app.route("/api/process", methods=["POST"])
def process_audio_endpoint():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files["audio"]
    upload_folder = 'uploads'
    os.makedirs(upload_folder, exist_ok=True)
    audio_path = os.path.join(upload_folder, audio_file.filename or "recording.wav")
    
    try:
        audio_file.save(audio_path)
        transcript = recognize_speech_from_file(audio_path)
        if not transcript:
             return jsonify({"transcript": "[Không nhận diện được]", "response": "Xin lỗi, tôi không thể nhận diện được âm thanh."})

        # Gọi hàm mới để tạo phản hồi bằng OpenAI
        generated_response = generate_response_with_llm(transcript)
        
        save_to_db(os.path.basename(audio_path), transcript, generated_response)
        
        return jsonify({"transcript": transcript, "response": generated_response})
    except Exception as e:
        logging.error(f"Lỗi trong API /api/process: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

# --- HÀM MAIN ---
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)