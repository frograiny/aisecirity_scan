# 📥 Hướng dẫn tải Datasets từ Kaggle

## 🎯 Datasets khuyên dùng

### 1. **SQL Injection Dataset** ✅
- 🔗 https://www.kaggle.com/datasets/sajid576/sql-injection-dataset
- 📊 Kích thước: ~150 samples
- 📝 Cột: `Sentence` (payload), `Label` (0=normal, 1=SQLi)

### 2. **XSS (Cross-Site Scripting) Dataset** ✅
- 🔗 https://www.kaggle.com/datasets/syedsaqlainhussain/cross-site-scripting-xss-dataset-for-deep-learning
- 📊 Kích thước: ~2,000+ samples
- 📝 Cột: `Sentence`, `Label`

### 3. **Web Application Payloads Dataset** 🔥 (Multi-Attack)
- 🔗 https://www.kaggle.com/datasets/cyberprince/web-application-payloads-dataset
- 📊 Kích thước: ~300 payloads (SQL Injection + XSS + Command Injection + **SSRF** + **Path Traversal**)
- 📝 Format: JSON, labeled by `type` & `severity`
- 📌 **BEST:** Có tất cả 5 loại attack trong 1 dataset!
- Cột: `id`, `description`, `payload`, `context`, `type`, `severity`

---

## ⚙️ Setup Kaggle API

### Step 1: Cài đặt**
```bash
pip install kaggle
```

### Step 2: Tạo Kaggle API Token
1. Truy cập: https://www.kaggle.com/settings/account
2. Cuộn xuống phần "API"
3. Nhấn **"Create New API Token"**
   - File `kaggle.json` sẽ được tải về

### Step 3: Copy file vào thư mục
```bash
# Windows
mkdir %USERPROFILE%\.kaggle
copy kaggle.json %USERPROFILE%\.kaggle\
icacls %USERPROFILE%\.kaggle\kaggle.json /grant %USERNAME%:F

# macOS/Linux
mkdir -p ~/.kaggle
cp kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

---

## 🚀 Cách tải tự động

### Option 1: Dùng script
```bash
cd d:\AI\clawweb\data
python download_datasets.py
```

### Option 2: Tải thủ công từng dataset
```bash
# Tải SQL Injection
kaggle datasets download -d sajid576/sql-injection-dataset -p ./sql_injection

# Tải XSS
kaggle datasets download -d syedsaqlainhussain/cross-site-scripting-xss-dataset-for-deep-learning -p ./xss

# Tải Web Payloads (chứa Command Injection + SSRF + Path Traversal)
kaggle datasets download -d cyberprince/web-application-payloads-dataset -p ./web_payloads

# Giải nén tất cả
for file in *.zip; do unzip "$file" && rm "$file"; done

# Hoặc Windows:
for /r %f in (*.zip) do powershell -Command "Expand-Archive '%f' -DestinationPath (Split-Path '%f')" && del "%f"
```

---

## 📁 Cấu trúc thư mục sau khi tải

```
d:\AI\clawweb\data\
├── sql_injection/
│   ├── sql_data_clean.csv  (hoặc tên file khác)
│   └── ...
├── xss/
│   ├── XSS_dataset.csv  (hoặc tên file khác)
│   └── ...
├── web_payloads/
│   ├── payloads.json  (hoặc payloads.csv)
│   ├── README.md
│   └── ...
├── command_injection/  (extract từ web_payloads nếu cần)
├── path_traversal/     (extract từ web_payloads nếu cần)
├── ssrf/               (extract từ web_payloads nếu cần)
└── download_datasets.py
```

---

## 💡 Các datasets Kaggle khác (nếu muốn)

### Path Traversal
- https://www.kaggle.com/datasets/mlg-ulb/creditcard (có dạng structured data)

### SSRF + Malware
- https://www.kaggle.com/datasets/cdeotte/image-classification-lstm
- https://www.kaggle.com/datasets/pcqq/malware-classification

### General Web Security
- https://www.kaggle.com/datasets/cdeotte/reading-data
- https://www.kaggle.com/datasets/ashok10437/url-dataset-for-malicious-urls-detection

---

## 🔄 Load data trong Notebook

Sau khi tải xong, update notebook:

```python
# Thay vì load từ GitHub:
# df_sqli = pd.read_csv("https://raw.githubusercontent.com/...")

# Load từ local:
df_sqli = pd.read_csv("./data/sql_injection/sql_data_clean.csv")
df_xss = pd.read_csv("./data/xss/XSS_dataset.csv")
```

---

## ⚠️ Troubleshooting

### ❌ "kaggle.json not found"
```bash
# Kiểm tra tồn tại:
dir %USERPROFILE%\.kaggle\

# Nếu không có, copy lại từ download
```

### ❌ "403 Forbidden"
- Token đã hết hạn → Tạo token mới
- Permission sai → Đảm bảo file có quyền đọc

### ❌ Tải quá lâu
- Kết nối internet yếu
- Thử tải từ browser rồi copy file vào thư mục `data`

---

## 📌 Lưu ý
- API token trong `kaggle.json` là **Private** - không commit lên Git!
- Thêm `~/.kaggle/` vào `.gitignore`
