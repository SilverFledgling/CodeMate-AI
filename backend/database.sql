/* --- FILE: backend/database.sql --- */

-- Xóa database cũ nếu tồn tại để tránh lỗi
DROP DATABASE IF EXISTS speech_recognition;

CREATE DATABASE speech_recognition;
USE speech_recognition;

CREATE TABLE history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    audio_filename VARCHAR(255) NOT NULL, -- Đổi tên cột để rõ ràng hơn
    transcript TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);