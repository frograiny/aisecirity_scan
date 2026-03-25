# 📘 Hướng Dẫn Sử Dụng AI WAF (WebG.py)

**Version**: 2.0  
**Last Updated**: 25/03/2026

---

## 🎯 Mục Đích

WebG.py là một **AI-powered Web Application Firewall** (WAF) được xây dựng bằng Flask + Bi-LSTM Deep Learning model. Nó có khả năng:

✅ Phát hiện các loại tấn công web: SQLi, XSS, Command Injection, Path Traversal, v.v.  
✅ Chặn requests độc hại trước khi chúng vào ứng dụng  
✅ Log các sự cố tấn công  
✅ Cung cấp API response chi tiết

---

## 📦 Cài Đặt & Chạy

### 1. **Điều Kiện Tiên Quyết**

```bash
# Cài Python 3.8+
python --version

# Cái packages cần thiết
pip install flask markupsafe tensorflow numpy scikit-learn
```

### 2. **Cấu Trúc Thư Mục**

```
D:\AI\clawweb\
├── webg.py                              # Main Flask WAF server
├── model/
│   ├── deep_learning_agent_core.keras   # Trained Bi-LSTM model
│   ├── tokenizer.pkl                    # Character tokenizer
│   └── label_encoder.pkl                # Label encoder
├── data/
│   ├── sql_injection/
│   ├── xss/
│   ├── oscommand/
│   ├── httpparagram/
│   └── web_payloads/
└── tongquat/                            # Documentation folder
    ├── IMPROVEMENTS.md
    ├── USAGE_GUIDE.md (this file)
    └── REPORT.md
```

### 3. **Khởi Chạy Server**

```bash
cd D:\AI\clawweb

# Run Flask server
python webg.py
```

**Output mong đợi**:
```
2026-03-25 10:30:45,123 - INFO - ✅ AI đã thức tỉnh và sẵn sàng bảo vệ Web!
2026-03-25 10:30:46,456 - INFO - 🌐 Đang khởi động Web Server tại http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

---

## 🧪 Testing

### **Test 1: Normal Request (Nên Pass)**

```bash
# Browser hoặc curl
curl "http://127.0.0.1:5000/search?q=hello"

# Response:
# <h3>Kết quả tìm kiếm: hello</h3>
# <p>Website xử lý an toàn vì AI xác nhận không có mã độc.</p>
```

✅ **Status**: 200 OK (Request thông qua)

---

### **Test 2: XSS Attack (Nên Block)**

```bash
curl "http://127.0.0.1:5000/search?q=<script>alert(1)</script>"
```

**Response** (nếu confidence ≥ 75%):
```json
{
  "error": "Access Denied by AI WAF",
  "reason": "Detected XSS",
  "confidence": "97.09%"
}
```

❌ **Status**: 403 Forbidden (Bị chặn)

**Server logs**:
```
2026-03-25 10:31:20 - WARNING - 🚨 XSS detected (Hash: a1b2c3d4, Confidence: 97.1%)
```

---

### **Test 3: SQL Injection (Nên Block)**

```bash
curl "http://127.0.0.1:5000/search?q=admin%27%20OR%201=1%20--"
```

**Response**:
```json
{
  "error": "Access Denied by AI WAF",
  "reason": "Detected SQLi",
  "confidence": "89.45%"
}
```

❌ **Status**: 403 Forbidden

---

### **Test 4: Path Traversal (Nên Block)**

```bash
curl "http://127.0.0.1:5000/search?q=../../../../etc/passwd"
```

**Response**:
```json
{
  "error": "Access Denied by AI WAF",
  "reason": "Detected Path Traversal",
  "confidence": "100.00%"
}
```

❌ **Status**: 403 Forbidden

---

### **Test 5: Command Injection (Nên Block)**

```bash
curl "http://127.0.0.1:5000/search?q=test%20%26%26%20cat%20/etc/passwd"
```

**Response**:
```json
{
  "error": "Access Denied by AI WAF",
  "reason": "Detected Command Injection",
  "confidence": "99.61%"
}
```

❌ **Status**: 403 Forbidden

---

## 🔌 API Endpoints

### **GET /**

**Mô tả**: Trang chủ lịch sự  
**URL**: `http://127.0.0.1:5000/`  
**Response**: HTML page

```html
<h1>🛡️ Website An Toàn - Protected by AI WAF</h1>
<p>Hệ thống được bảo vệ bởi AI Trinh Sát (Bi-LSTM)</p>
<p><a href="/search?q=hello">Try search</a></p>
```

**Status**: 200 OK

---

### **GET /search**

**Mô tả**: Search endpoint được bảo vệ  
**URL**: `GET /search?q=<query>`  
**Parameters**:
- `q` (string): Search query

**Responses**:

#### ✅ Success (Normal query):
```
Status: 200 OK
Body: <h3>Kết quả tìm kiếm: {safe_query}</h3>...
```

#### ❌ Blocked (Attack detected):
```
Status: 403 Forbidden
Body: {
  "error": "Access Denied by AI WAF",
  "reason": "Detected {attack_type}",
  "confidence": "{confidence}%"
}
```

**Example**:
```bash
# Normal
curl "http://127.0.0.1:5000/search?q=python"
# → 200 OK

# Attack
curl "http://127.0.0.1:5000/search?q=<script>alert('xss')</script>"
# → 403 Forbidden
```

---

## 📊 Monitoring & Logs

### **Log Levels**

**INFO** - Thông tin chung:
```
INFO: ✅ AI đã thức tỉnh và sẵn sàng bảo vệ Web!
INFO: ⚠️ Low confidence threat: XSS (65.0%)
```

**WARNING** - Cảnh báo (Attack detected):
```
WARNING: 🚨 XSS detected (Hash: a1b2c3d4, Confidence: 97.1%)
```

**ERROR** - Lỗi nghiêm trọng:
```
ERROR: ❌ Lỗi: Không tìm thấy não AI. Chi tiết: FileNotFoundError
ERROR: Error scanning payload: ValueError - ...
```

### **Log Format**

```
[TIMESTAMP] - [LEVEL] - [MESSAGE]
2026-03-25 10:31:20 - WARNING - 🚨 XSS detected (Hash: a1b2c3d4, Confidence: 97.1%)
```

### **Tìm Logs**

**Console output** (khi chạy Flask):
```bash
python webg.py  # Logs xuất ra console
```

**To file**:
```python
# Thêm vào webg.py
handler = logging.FileHandler('waf.log')
logger.addHandler(handler)
```

---

## ⚙️ Configuration

### **Thay Đổi Settings**

**File**: `webg.py`  
**Section**: Lines 19-21

```python
# ===== CONFIG =====
MODEL_DIR = r"D:\AI\clawweb\model"      # Đường dẫn model
MAX_LEN = 150                            # Max input length
CONFIDENCE_THRESHOLD = 75.0              # Ngưỡng chặn (0-100%)
```

### **Tuning Confidence Threshold**

**High Threshold (≥85%)**:
```python
CONFIDENCE_THRESHOLD = 85.0
```
- ✅ Ít false positives
- ❌ Có thể bypass attack yếu

**Low Threshold (≤65%)**:
```python
CONFIDENCE_THRESHOLD = 65.0
```
- ✅ Xác định mọi attack
- ❌ Nhiều false positives, user experience tệ

**Recommended**: **75.0** (Default) - Cân bằng tốt

---

## 🚨 Troubleshooting

### **Lỗi 1: Model File Not Found**

**Lỗi**:
```
ERROR: ❌ Lỗi: Không tìm thấy não AI. Chi tiết: FileNotFoundError: ...
```

**Giải pháp**:
1. Chạy `projectai.ipynb` để train & save model
2. Kiểm tra model files tồn tại:
   ```bash
   ls D:\AI\clawweb\model\
   # Output: deep_learning_agent_core.keras, tokenizer.pkl, label_encoder.pkl
   ```
3. Update `MODEL_DIR` trong `webg.py`

---

### **Lỗi 2: Port Already In Use**

**Lỗi**:
```
OSError: [Errno 10048] Only one usage of each socket address
```

**Giải pháp**:
```bash
# Kill process sử dụng port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Hoặc change port trong webg.py:
app.run(port=8000)  # Use port 8000 instead
```

---

### **Lỗi 3: False Positive Too High**

**Triệu chứng**: Normal URLs bị block  
**Nguyên nhân**: Model không tốt hoặc threshold quá thấp

**Giải pháp**:
```python
# Tăng threshold (chỉ block khi rất chắc chắn)
CONFIDENCE_THRESHOLD = 80.0  # From 75.0 to 80.0
```

---

### **Lỗi 4: Server Chậm / Timeout**

**Triệu chứng**: Response lâu, connection timeout  
**Nguyên nhân**: Model inference chậm, hoặc single-threaded

**Kiểm tra**:
- Có dùng `@tf.function` không? (Nên có)
- Có dùng `threaded=True` không? (Nên có)

**Giải pháp**:
```python
# Trong webg.py (nên có sẵn v2.0)
@tf.function
def scan_payload(payload):
    ...

app.run(debug=False, port=5000, threaded=True)
```

---

## 🔒 Security Best Practices

### **1. Change Default Port**

```python
# Default 5000 dễ bị bruteforce
app.run(port=5000)  # ❌ Not recommended

# Change to uncommon port
app.run(port=8731)  # ✅ Better
```

### **2. Use HTTPS**

```python
from flask_talisman import Talisman
Talisman(app)  # Enforce HTTPS

# Or with SSL:
app.run(ssl_context='adhoc')  # Requires pyopenssl
```

### **3. Rate Limiting**

```python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=get_remote_address)

@app.route('/search')
@limiter.limit("10 per minute")
def search():
    ...
```

### **4. Environment Variables**

```python
import os

MODEL_DIR = os.getenv('MODEL_DIR', r"D:\AI\clawweb\model")
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '75.0'))
```

---

## 📈 Performance Metrics

### **Typical Latency**

```
Request comes in
    ↓
Middleware check (firewall_middleware): ~35ms
    ↓
Model inference (scan_payload): ~35ms
    ↓
Route handler: ~2ms
    ↓
Total latency: ~72ms ✅
```

### **Capacity**

- **Single request**: ~72ms
- **Concurrent (threaded)**: ~100 requests/sec
- **Requests/day**: ~8.6 million

---

## 🎓 Examples

### **CURL Examples**

```bash
# 1. Normal search
curl "http://127.0.0.1:5000/search?q=machine%20learning"

# 2. XSS payload
curl "http://127.0.0.1:5000/search?q=%3Cscript%3Ealert(1)%3C/script%3E"

# 3. SQLi payload
curl "http://127.0.0.1:5000/search?q=admin%27%20OR%20%271%27=%271"

# 4. Multiple parameters
curl "http://127.0.0.1:5000/search?q=hello&sort=name&limit=10"
```

### **Python Requests**

```python
import requests

# Normal
r = requests.get("http://127.0.0.1:5000/search", params={"q": "hello"})
print(r.status_code)  # 200
print(r.text)

# Attack
r = requests.get("http://127.0.0.1:5000/search", params={"q": "<script>alert(1)</script>"})
print(r.status_code)  # 403
print(r.json())
# {"error": "Access Denied by AI WAF", "reason": "Detected XSS", "confidence": "97.09%"}
```

---

## 📞 Support & Documentation

**Related Files**:
- [IMPROVEMENTS.md](./IMPROVEMENTS.md) - Chi tiết cải thiện
- [REPORT.md](./REPORT.md) - Báo cáo training model
- [projectai.ipynb](../projectai.ipynb) - Training notebook
- [webg.py](../webg.py) - Main WAF code

**Issues**:
1. Check logs first: `python webg.py`
2. Verify model files exist
3. Check port availability
4. Update confidence threshold

---

## 🎯 Next Steps

1. ✅ Start WAF: `python webg.py`
2. ✅ Test endpoints (see Testing section)
3. ✅ Monitor logs
4. ✅ Adjust config if needed
5. ✅ Deploy to production (add HTTPS, rate limiting, etc.)

**Ready to protect your web application from AI-powered Web Application Firewall!** 🛡️

---

*Generated: 25/03/2026 - WebG.py v2.0 Usage Guide*
