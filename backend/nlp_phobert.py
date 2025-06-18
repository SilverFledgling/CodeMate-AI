import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from transformers import WhisperForConditionalGeneration, WhisperProcessor, AutoTokenizer, AutoModelForSequenceClassification
import torch
import librosa
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# --- CÀI ĐẶT CƠ BẢN ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__,
            template_folder='../frontend',
            static_folder='../frontend',
            static_url_path='')
CORS(app)

# --- CẤU HÌNH DATABASE ---
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "speech_recognition" # Sửa tên database lại cho đúng với file .sql
}

# --- TẢI MODEL (CHỈ TẢI MỘT LẦN KHI SERVER KHỞI ĐỘNG) ---
logging.info("Bắt đầu tải các mô hình...")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logging.info(f"Sử dụng thiết bị: {DEVICE}")

try:
    # 1. Tải mô hình Whisper đã được fine-tune
    whisper_model_path = "ElfiDeeper/whisper-base-finetuned-vietnamese"
    whisper_processor = WhisperProcessor.from_pretrained(whisper_model_path)
    whisper_model = WhisperForConditionalGeneration.from_pretrained(whisper_model_path).to(DEVICE)
    logging.info(f"Đã tải thành công mô hình Whisper từ: {whisper_model_path}")

    # 2. Tải mô hình PhoBERT để phân loại ý định
    phobert_model_path = "vinai/phobert-base"
    phobert_tokenizer = AutoTokenizer.from_pretrained(phobert_model_path)
    phobert_model = AutoModelForSequenceClassification.from_pretrained(phobert_model_path, num_labels=3).to(DEVICE)
    logging.info(f"Đã tải thành công mô hình PhoBERT từ: {phobert_model_path}")
except Exception as e:
    logging.error(f"LỖI NGHIÊM TRỌNG: Không thể tải mô hình khi khởi động. Lỗi: {e}")

# --- CÁC HÀM XỬ LÝ DATABASE ---
def save_to_db(audio_filename, transcript, response):
    """Lưu kết quả vào database."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = "INSERT INTO history (audio_path, transcript, response) VALUES (%s, %s, %s)"
        cursor.execute(query, (audio_filename, transcript, response))
        conn.commit()
        logging.info(f"Đã lưu vào DB: {audio_filename}")
    except Error as e:
        logging.error(f"Lỗi khi lưu vào DB: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# --- CÁC HÀM XỬ LÝ AI ---
def recognize_speech_from_file(audio_path):
    try:
        speech_array, _ = librosa.load(audio_path, sr=16000)
        input_features = whisper_processor(speech_array, sampling_rate=16000, return_tensors="pt").input_features.to(DEVICE)
        predicted_ids = whisper_model.generate(input_features, max_length=256)
        transcript = whisper_processor.batch_decode(predicted_ids, skip_special_tokens=True, normalize=True)[0]
        logging.info(f"Nhận diện thành công: {transcript}")
        return transcript.strip()
    except Exception as e:
        logging.error(f"Lỗi khi nhận diện giọng nói: {e}")
        return None

def classify_intent(text):
    try:
        inputs = phobert_tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(DEVICE)
        outputs = phobert_model(**inputs)
        predictions = torch.argmax(outputs.logits, dim=1)
        intent_map = {0: "yêu cầu", 1: "hỏi", 2: "chào hỏi"}
        intent = intent_map.get(predictions.item(), "không xác định")
        logging.info(f"Văn bản '{text}' -> Ý định: {intent}")
        return intent
    except Exception as e:
        logging.error(f"Lỗi khi phân loại ý định: {e}")
        return "không xác định"

def generate_response(text):
    intent = classify_intent(text)
    if intent == "chào hỏi":
        return "Xin chào! Tôi có thể giúp gì cho bạn?"
    elif intent == "hỏi":
        return "Đây là một câu hỏi. Tôi sẽ tìm thông tin cho bạn."
    else:
        return "Tôi đã ghi nhận yêu cầu của bạn."

# --- API ENDPOINTS (CẬP NHẬT ĐỂ GỌI HÀM LƯU DB) ---
@app.route('/')
def index():
    return render_template("index.html")

@app.route("/api/process", methods=["POST"])
def process_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    audio_file = request.files["audio"]
    upload_folder = 'uploads'
    os.makedirs(upload_folder, exist_ok=True)
    audio_path = os.path.join(upload_folder, audio_file.filename)
    try:
        audio_file.save(audio_path)
        logging.info(f"Đã lưu file âm thanh tại: {audio_path}")

        transcript = recognize_speech_from_file(audio_path)
        if transcript is None or transcript == "":
             return jsonify({"transcript": "[Không nhận diện được]", "response": "Xin lỗi, tôi không thể nhận diện được âm thanh. Vui lòng thử lại."})

        response_text = generate_response(transcript)
        
        # --- GỌI HÀM LƯU VÀO DATABASE ---
        save_to_db(audio_file.filename, transcript, response_text)
        
        return jsonify({"transcript": transcript, "response": response_text})
    except Exception as e:
        logging.error(f"Lỗi trong API /api/process: {e}")
        return jsonify({"error": "An internal error occurred"}), 500
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

# --- HÀM MAIN (THÊM KIỂM TRA KẾT NỐI DB KHI KHỞI ĐỘNG) ---
if __name__ == "__main__":
    # Kiểm tra kết nối database trước khi chạy app
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            logging.info("Kết nối MySQL thành công khi khởi động.")
            conn.close()
    except Error as e:
        logging.error(f"LỖI KẾT NỐI DATABASE: Không thể kết nối tới MySQL. Vui lòng kiểm tra lại. Lỗi: {e}")
        # Dừng không chạy app nếu không kết nối được DB
    else:
        logging.info("Khởi động Flask server...")
        app.run(debug=True, host="0.0.0.0", port=5000)