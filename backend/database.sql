CREATE DATABASE speech_recognition;
USE speech_recognition;

CREATE TABLE history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    audio_path VARCHAR(255) NOT NULL,
    transcript TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);