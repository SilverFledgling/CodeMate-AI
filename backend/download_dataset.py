import logging
from datasets import load_dataset, DownloadConfig
import os

# Thiết lập logging
logging.basicConfig(
    filename='D:\\TTCS\\backend\\download.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Đường dẫn cache
dataset_path = r"D:\TTCS\backend\uploads"
dataset_cache = os.path.join(dataset_path, "doof-ferb___vlsp2020_vinai_100h")

try:
    # Cấu hình download với số lần thử lại
    download_config = DownloadConfig(max_retries=5)
    # Tải dataset
    ds = load_dataset("doof-ferb/vlsp2020_vinai_100h", cache_dir=dataset_path, download_config=download_config)
    logging.info(f"Đã tải dataset thành công và lưu tại {dataset_path}")
    # Lưu dataset vào disk để sử dụng sau này
    ds.save_to_disk(dataset_cache)
    logging.info(f"Đã lưu dataset vào {dataset_cache}")
except Exception as e:
    logging.error(f"Lỗi khi tải hoặc lưu dataset: {e}")
    raise e