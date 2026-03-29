#!/usr/bin/env python3
r"""
Script tải datasets từ Kaggle
Trước tiên cần:
1. pip install kaggle
2. Tạo API token từ https://www.kaggle.com/settings/account
3. Copy ~/.kaggle/kaggle.json vào C:\Users\<username>\.kaggle\kaggle.json
"""

import os
import subprocess
import shutil

# Danh sách datasets
DATASETS = {
    "sql_injection": "sajid576/sql-injection-dataset",
    "xss": "syedsaqlainhussain/cross-site-scripting-xss-dataset-for-deep-learning",
    "web_payloads": "cyberprince/web-application-payloads-dataset",  # Multi-attack: Command Injection + SSRF + Path Traversal
}

def download_dataset(dataset_key, dataset_path):
    """Tải một dataset từ Kaggle"""
    print(f"\n📥 Tải {dataset_key}...")
    try:
        # Tạo thư mục
        os.makedirs(f"./{dataset_key}", exist_ok=True)
        
        # Tải vào thư mục riêng với tên tạm
        temp_dir = f"./{dataset_key}_temp"
        os.makedirs(temp_dir, exist_ok=True)
        cmd = f'kaggle datasets download -d {dataset_path} -p {temp_dir}'
        os.system(cmd)
        
        # Giải nén 
        import zipfile
        import glob
        zip_files = glob.glob(f"{temp_dir}/*.zip")
        for zip_file in zip_files:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(f"./{dataset_key}")
        
        # Xóa temp
        import shutil
        shutil.rmtree(temp_dir)
        print(f"✅ Giải nén xong: ./{dataset_key}")
    except Exception as e:
        print(f"❌ Lỗi tải {dataset_key}: {e}")

def setup_kaggle_api():
    """Kiểm tra xem Kaggle API có được setup chưa"""
    kaggle_json = os.path.expanduser("~/.kaggle/kaggle.json")
    if not os.path.exists(kaggle_json):
        print("⚠️  kaggle.json không tìm thấy!")
        print("Hướng dẫn setup:")
        print("1. Truy cập https://www.kaggle.com/settings/account")
        print("2. Nhấn 'Create New API Token' để tải kaggle.json")
        print(f"3. Copy kaggle.json vào: {kaggle_json}")
        return False
    return True

def main():
    print("🚀 Kaggle Datasets Downloader")
    print("=" * 50)
    
    # Kiểm tra Kaggle API
    if not setup_kaggle_api():
        print("\n❌ Setup Kaggle API trước khi chạy script!")
        return
    
    # Tạo thư mục
    for dataset_key in DATASETS:
        os.makedirs(f"./data/{dataset_key}", exist_ok=True)
    
    # Tải từng dataset
    for dataset_key, dataset_path in DATASETS.items():
        download_dataset(dataset_key, dataset_path)
    
    print("\n✅ Tải hoàn tất!")
    print("\n📂 Cấu trúc thư mục:")
    for root, dirs, files in os.walk("."):
        level = root.replace(".", "").count(os.sep)
        if level > 2:
            continue
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = " " * 2 * (level + 1)
        for f in files[:3]:
            print(f"{sub_indent}{f}")
        if len(files) > 3:
            print(f"{sub_indent}... ({len(files) - 3} file khác)")

if __name__ == "__main__":
    main()
