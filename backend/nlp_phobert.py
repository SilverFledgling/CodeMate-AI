import os
import logging
from flask import Flask, request, jsonify
import whisper
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from datasets import load_dataset, load_from_disk, DownloadConfig
import torch
import torch.quantization
import mysql.connector
from mysql.connector import Error
import soundfile as sf
import numpy as np
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    filename='D:\\TTCS\\backend\\app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# Kết nối MySQL
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "2003",
    "database": "speech_recognition_new"
}

# Tải dữ liệu từ Hugging Face
dataset_path = r"D:\TTCS\backend\uploads"
dataset_cache = os.path.join(dataset_path, "doof-ferb___vlsp2020_vinai_100h")
try:
    # Thử tải từ disk trước
    ds = load_from_disk(dataset_cache)
    logging.info(f"Đã tải dữ liệu từ {dataset_cache}")
except FileNotFoundError:
    # Nếu không thành công, tải từ Hugging Face
    logging.info(f"Dataset không tìm thấy tại {dataset_cache}. Tải từ Hugging Face...")
    try:
        download_config = DownloadConfig(max_retries=5)  # Use max_retries instead of num_retries
        ds = load_dataset("doof-ferb/vlsp2020_vinai_100h", cache_dir=dataset_path, download_config=download_config)
        ds.save_to_disk(dataset_cache)
        logging.info(f"Đã tải và lưu dữ liệu từ Hugging Face vào {dataset_cache}")
    except Exception as e:
        logging.error(f"Lỗi khi tải dữ liệu từ Hugging Face: {e}")
        raise e
except Exception as e:
    logging.error(f"Lỗi khi tải dữ liệu từ disk: {e}")
    raise e

# Tải và fine-tune mô hình Whisper
model = whisper.load_model("base")
logging.info("Đã tải mô hình Whisper base")

# Fine-tune Whisper (chỉ chạy một lần, sau đó lưu mô hình)
def fine_tune_whisper():
    # Chuẩn bị dữ liệu huấn luyện
    def prepare_dataset(batch):
        try:
            audio_data = batch["audio"]["array"]
            batch["audio_data"] = whisper.pad_or_trim(whisper.log_mel_spectrogram(audio_data))
            batch["labels"] = batch["transcription"]
            return batch
        except Exception as e:
            logging.error(f"Lỗi khi chuẩn bị dataset: {e}")
            raise e

    try:
        train_dataset = ds["train"].map(prepare_dataset, remove_columns=["audio", "transcription"])
        
        training_args = TrainingArguments(
            output_dir="D:\\TTCS\\backend\\whisper_finetuned",
            num_train_epochs=5,
            per_device_train_batch_size=4,
            learning_rate=1e-5,
            save_steps=500,
            save_total_limit=2,
            logging_steps=100,
        )
        
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
        )
        
        trainer.train()
        trainer.save_model("D:\\TTCS\\backend\\whisper_finetuned")
        logging.info("Đã fine-tune và lưu mô hình Whisper")
    except Exception as e:
        logging.error(f"Lỗi khi fine-tune mô hình Whisper: {e}")
        raise e

# Kiểm tra xem mô hình đã được fine-tune chưa, nếu chưa thì fine-tune
if not os.path.exists("D:\\TTCS\\backend\\whisper_finetuned"):
    fine_tune_whisper()
else:
    model = whisper.load_model("D:\\TTCS\\backend\\whisper_finetuned")
    logging.info("Đã tải mô hình Whisper đã fine-tune")

# Tối ưu hóa mô hình Whisper
model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
logging.info("Đã tối ưu hóa mô hình Whisper bằng quantization")

# Tải PhoBERT
try:
    tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base")
    nlp_model = AutoModelForSequenceClassification.from_pretrained("vinai/phobert-base", num_labels=3)
    logging.info("Đã tải mô hình PhoBERT")
except Exception as e:
    logging.error(f"Lỗi khi tải mô hình PhoBERT: {e}")
    raise e

# Hàm lưu vào MySQL
def save_to_db(audio_path, transcript, response):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = "INSERT INTO history (audio_path, transcript, response) VALUES (%s, %s, %s)"
        cursor.execute(query, (audio_path, transcript, response))
        conn.commit()
        logging.info(f"Đã lưu vào DB: {audio_path}, {transcript}, {response}")
    except Error as e:
        logging.error(f"Lỗi khi lưu vào DB: {e}")
    finally:
        cursor.close()
        conn.close()

# Hàm nhận diện giọng nói
def recognize_speech(audio_path):
    try:
        start_time = datetime.now()
        result = model.transcribe(audio_path, language="vi")
        transcript = result["text"]
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        logging.info(f"Nhận diện giọng nói: {transcript}, Thời gian xử lý: {processing_time} giây")
        return transcript
    except Exception as e:
        logging.error(f"Lỗi khi nhận diện giọng nói: {e}")
        raise e

# Hàm phân loại ý định
def classify_intent(text):
    try:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        outputs = nlp_model(**inputs)
        predictions = torch.argmax(outputs.logits, dim=1)
        intent_map = {0: "chào hỏi", 1: "hỏi", 2: "yêu cầu"}
        return intent_map[predictions.item()]
    except Exception as e:
        logging.error(f"Lỗi khi phân loại ý định: {e}")
        raise e

# Hàm tạo phản hồi
def generate_response(text):
    try:
        intent = classify_intent(text)
        logging.info(f"Ý định: {intent}")
        if intent == "chào hỏi":
            return "Xin chào! Rất vui được trò chuyện với bạn."
        elif intent == "hỏi":
            return "Hôm nay trời nắng, nhiệt độ khoảng 30°C."
        else:
            return "Tôi sẽ cố gắng thực hiện yêu cầu của bạn."
    except Exception as e:
        logging.error(f"Lỗi khi tạo phản hồi: {e}")
        raise e

# API xử lý âm thanh
@app.route("/api/process", methods=["POST"])
def process_audio():
    try:
        if "audio" not in request.files:
            logging.warning("Không có file âm thanh trong yêu cầu")
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files["audio"]
        if not audio_file.filename.endswith(('.wav', '.mp3')):
            logging.warning(f"Định dạng file không hỗ trợ: {audio_file.filename}")
            return jsonify({"error": "Only WAV or MP3 files are supported"}), 400

        audio_path = os.path.join("uploads", audio_file.filename)
        audio_file.save(audio_path)
        logging.info(f"Đã lưu file âm thanh tại: {audio_path}")

        transcript = recognize_speech(audio_path)
        response = generate_response(transcript)
        save_to_db(audio_path, transcript, response)

        return jsonify({"transcript": transcript, "response": response})
    except Exception as e:
        logging.error(f"Lỗi trong API /api/process: {e}")
        return jsonify({"error": str(e)}), 500

def main():
    logging.info("Khởi động ứng dụng Speech Recognition...")
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            logging.info("Kết nối MySQL thành công")
        conn.close()
    except Error as e:
        logging.error(f"Lỗi kết nối MySQL: {e}")
        return
    
    if "train" in ds:
        logging.info(f"Tập dữ liệu train có {len(ds['train'])} mẫu")
    else:
        logging.error("Không tìm thấy tập train trong dữ liệu")
        return
    
    app.run(debug=True, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()