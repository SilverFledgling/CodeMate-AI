from datasets import load_from_disk
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

dataset_cache = r"D:\TTCS\backend\uploads\doof-ferb___vlsp2020_vinai_100h"
ds = load_from_disk(dataset_cache)
logging.info(f"Dataset keys: {ds['train'].column_names}")
logging.info(f"First example: {ds['train'][0]}")
logging.info(f"Second example: {ds['train'][1]}")