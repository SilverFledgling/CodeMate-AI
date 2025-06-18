# === NỘI DUNG ĐÚNG CỦA FILE fine_tune_on_colab.py ===

# Step 1: Các thư viện cần thiết
# Trên máy local, bạn cần cài đặt các thư viện này bằng file requirements.txt
# !pip install -q "datasets>=2.19.0" \
#  "transformers==4.38.2" \
#  "accelerate==0.29.3" \
#  "peft==0.9.0" \
#  "librosa"

# !pip uninstall -y hf-xet

import os
import logging
import sys
import numpy as np
from datasets import load_dataset, load_from_disk
from transformers import WhisperForConditionalGeneration, WhisperProcessor, Trainer, TrainingArguments
# from google.colab import drive # Dòng này chỉ dùng cho Colab
import torch
import gc
import shutil
from huggingface_hub import login
import librosa

# ---- PHẦN NÀY CHỦ YẾU DÙNG CHO COLAB ----
# drive.mount('/content/drive', force_remount=True)
# !nvidia-smi # Lệnh này dùng để kiểm tra GPU, chỉ chạy được trong terminal hoặc notebook
# ---------------------------------------------

# Mount Google Drive
drive.mount('/content/drive', force_remount=True)

# Authenticate with Hugging Face
HF_TOKEN = "hf_************************************"  # Replace with your actual token of your Hugging Face
login(HF_TOKEN)

# ---- Logging Setup ----
log_file = "/content/drive/MyDrive/finetune_production.log"

# Clear previous log file if it exists
if os.path.exists(log_file):
    os.remove(log_file)

logging.basicConfig(
    level=logging.INFO, # Use INFO for production, DEBUG for debugging
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

logger.info("--- Starting new fine-tuning session with updated libraries ---")
!nvidia-smi

def fine_tune_whisper():
    # Use local Colab storage for caching. It's faster and more reliable.
    local_cache_dir = "/content/huggingface_cache"
    processed_dataset_drive_path = "/content/drive/MyDrive/processed_dataset_vi_common_voice"

    try:
        # Check if the dataset has already been processed and saved to Drive
        if os.path.exists(processed_dataset_drive_path):
            logger.info("Loading processed dataset from Google Drive: %s", processed_dataset_drive_path)
            train_dataset = load_from_disk(processed_dataset_drive_path)
            logger.info("Successfully loaded processed dataset from disk.")
        else:
            logger.info("Processed dataset not found. Starting download and processing from Hugging Face Hub...")
            ds = load_dataset(
                "mozilla-foundation/common_voice_13_0",
                "vi",
                split="train",
                cache_dir=local_cache_dir,
                token=HF_TOKEN,
            )
            logger.info("Dataset downloaded successfully!")

            processor = WhisperProcessor.from_pretrained("openai/whisper-base", language="vi", task="transcribe")

            def prepare_dataset(batch):
                audio = batch["audio"]
                # Resample audio to 16kHz
                audio_array = librosa.resample(np.array(audio["array"]), orig_sr=audio["sampling_rate"], target_sr=16000)

                # Process audio and text
                batch["input_features"] = processor(audio_array, sampling_rate=16000).input_features[0]
                batch["labels"] = processor(text=batch["sentence"]).input_ids
                return batch

            logger.info("Starting to preprocess (map) the dataset. This may take a while...")
            train_dataset = ds.map(
                prepare_dataset,
                remove_columns=ds.column_names,
                num_proc=os.cpu_count() # Use all available CPU cores for faster processing
            )
            logger.info("Dataset preprocessing complete.")

            logger.info("Saving processed dataset to Google Drive for future use: %s", processed_dataset_drive_path)
            train_dataset.save_to_disk(processed_dataset_drive_path)
            logger.info("Successfully saved processed dataset.")

        gc.collect()

        logger.info("--- Starting model training ---")
        processor = WhisperProcessor.from_pretrained("openai/whisper-base", language="vi", task="transcribe")
        model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-base")
        model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(language="vi", task="transcribe")
        logger.info("Loaded Whisper processor and base model for training.")

        # Define the data collator
        def data_collator(features):
            input_features = [{"input_features": feature["input_features"]} for feature in features]
            labels = [{"input_ids": feature["labels"]} for feature in features]

            batch = processor.feature_extractor.pad(input_features, return_tensors="pt")
            label_batch = processor.tokenizer.pad(labels, return_tensors="pt")

            # Replace padding with -100 to ignore loss correctly
            labels = label_batch["input_ids"].masked_fill(label_batch.attention_mask.ne(1), -100)

            batch["labels"] = labels
            return batch

        training_args = TrainingArguments(
            output_dir="/content/drive/MyDrive/whisper_finetuned_vi",
            num_train_epochs=3,
            per_device_train_batch_size=4, # Increased batch size slightly, adjust if you get OOM errors
            gradient_accumulation_steps=4,
            learning_rate=1e-5,
            warmup_steps=500,
            save_steps=1000,
            save_total_limit=2,
            logging_steps=100,
            fp16=True, # Use mixed-precision training
            report_to=["none"], # Can be changed to "tensorboard", "wandb" etc.
            dataloader_num_workers=2,
            gradient_checkpointing=True, # Saves memory
            max_grad_norm=1.0,
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            data_collator=data_collator,
        )

        logger.info("Trainer initialized. Starting training...")
        trainer.train()
        logger.info("Training finished.")

        torch.cuda.empty_cache()
        gc.collect()

        logger.info("Saving final model and processor...")
        trainer.save_model("/content/drive/MyDrive/whisper_finetuned_vi/final_model")
        processor.save_pretrained("/content/drive/MyDrive/whisper_finetuned_vi/final_model")
        logger.info("Model and processor saved successfully.")

    except Exception as e:
        logger.error("A critical error stopped the fine-tuning process.", exc_info=True)
    finally:
        logger.info("--- Fine-tuning session finished ---")
        if os.path.exists(local_cache_dir):
            shutil.rmtree(local_cache_dir)
            logger.info("Cleaned up local cache directory.")
        logging.shutdown()
        if os.path.exists(log_file):
            shutil.copyfile(log_file, f"{log_file}.final.log")

if __name__ == "__main__":
    fine_tune_whisper()