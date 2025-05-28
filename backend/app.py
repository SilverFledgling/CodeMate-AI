import os
import logging
import sys
from datasets import load_from_disk
import numpy as np
import whisper
from transformers import Trainer, TrainingArguments
from multiprocess import freeze_support

# Thiết lập logging
logging.basicConfig(
    filename='D:\\TTCS\\backend\\finetune.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True,
    filemode='w'  # Overwrite log file
)
# Ensure logs are written immediately
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(handler)

def fine_tune_whisper():
    dataset_cache = r"D:\TTCS\backend\uploads\doof-ferb___vlsp2020_vinai_100h"
    try:
        ds = load_from_disk(dataset_cache)
        logging.info(f"Đã tải dữ liệu từ {dataset_cache}")
    except Exception as e:
        logging.error(f"Lỗi khi tải dữ liệu từ disk: {e}")
        raise e
    
    def prepare_dataset_batched(examples):
        processed = []
        for idx, example in enumerate(examples):
            try:
                audio_data = example["audio"]["array"]
                if audio_data.size == 0:
                    logging.warning(f"Bỏ qua sample {idx}: mảng âm thanh rỗng")
                    continue
                logging.debug(f"Sample {idx}: shape={audio_data.shape}, dtype={audio_data.dtype}")
                audio_data = np.asarray(audio_data, dtype=np.float32)
                mel = whisper.log_mel_spectrogram(audio_data)
                processed.append({
                    "audio_data": whisper.pad_or_trim(mel),
                    "labels": example["transcription"]
                })
            except Exception as e:
                logging.error(f"Lỗi khi xử lý sample {idx}: {e}, sample={example}")
                raise e
        return processed
    
    model = whisper.load_model("base")
    logging.info("Đã tải mô hình Whisper base")
    
    try:
        # Use smaller subset for debugging (2,000 examples)
        train_dataset = ds["train"].select(range(2000)).map(
            prepare_dataset_batched,
            batched=True,
            batch_size=50,
            remove_columns=["audio", "transcription"],
            num_proc=1
        )
        logging.info("Đã chuẩn bị dataset với num_proc=1, batching, 2000 examples")
        
        training_args = TrainingArguments(
            output_dir="D:\\TTCS\\backend\\whisper_finetuned",
            num_train_epochs=5,
            per_device_train_batch_size=2,
            learning_rate=1e-5,
            save_steps=500,
            save_total_limit=2,
            logging_steps=100,
            fp16=True,
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

if __name__ == "__main__":
    freeze_support()
    fine_tune_whisper()import os
import logging
import sys
from datasets import load_from_disk
import numpy as np
import whisper
from transformers import Trainer, TrainingArguments
from multiprocess import freeze_support

# Thiết lập logging
logging.basicConfig(
    filename='D:\\TTCS\\backend\\finetune.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True,
    filemode='w'  # Overwrite log file
)
# Ensure logs are written immediately
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(handler)

def fine_tune_whisper():
    dataset_cache = r"D:\TTCS\backend\uploads\doof-ferb___vlsp2020_vinai_100h"
    try:
        ds = load_from_disk(dataset_cache)
        logging.info(f"Đã tải dữ liệu từ {dataset_cache}")
    except Exception as e:
        logging.error(f"Lỗi khi tải dữ liệu từ disk: {e}")
        raise e
    
    def prepare_dataset_batched(examples):
        processed = []
        for idx, example in enumerate(examples):
            try:
                audio_data = example["audio"]["array"]
                if audio_data.size == 0:
                    logging.warning(f"Bỏ qua sample {idx}: mảng âm thanh rỗng")
                    continue
                logging.debug(f"Sample {idx}: shape={audio_data.shape}, dtype={audio_data.dtype}")
                audio_data = np.asarray(audio_data, dtype=np.float32)
                mel = whisper.log_mel_spectrogram(audio_data)
                processed.append({
                    "audio_data": whisper.pad_or_trim(mel),
                    "labels": example["transcription"]
                })
            except Exception as e:
                logging.error(f"Lỗi khi xử lý sample {idx}: {e}, sample={example}")
                raise e
        return processed
    
    model = whisper.load_model("base")
    logging.info("Đã tải mô hình Whisper base")
    
    try:
        # Use smaller subset for debugging (2,000 examples)
        train_dataset = ds["train"].select(range(2000)).map(
            prepare_dataset_batched,
            batched=True,
            batch_size=50,
            remove_columns=["audio", "transcription"],
            num_proc=1
        )
        logging.info("Đã chuẩn bị dataset với num_proc=1, batching, 2000 examples")
        
        training_args = TrainingArguments(
            output_dir="D:\\TTCS\\backend\\whisper_finetuned",
            num_train_epochs=5,
            per_device_train_batch_size=2,
            learning_rate=1e-5,
            save_steps=500,
            save_total_limit=2,
            logging_steps=100,
            fp16=True,
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

if __name__ == "__main__":
    freeze_support()
    fine_tune_whisper()