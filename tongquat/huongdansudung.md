# 🛡️ Hướng Dẫn Tích Hợp AI WAF (Web Application Firewall)

Chào anh em! 👋 Đây là tài liệu hướng dẫn cách khởi chạy và kết nối với hệ thống **Trạm Gác AI (AI WAF Agent)**.

Hệ thống này sử dụng mô hình **Deep Learning (Bi-LSTM)** để quét và chặn đứng các loại mã độc:
- ✅ SQLi (SQL Injection)
- ✅ XSS (Cross-Site Scripting)
- ✅ Path Traversal
- ✅ Command Injection
- ✅ SSRF (Server-Side Request Forgery)

...ngay từ cửa ngõ, trước khi nó kịp chạm vào Database!

---

## ⚙️ 1. Yêu Cầu Hệ Thống

### Dành cho người chạy Backend AI

Để chạy được con Agent này, máy cần cài đặt:
- **Python 3.8+**
- **Các thư viện Machine Learning**

### Cài đặt thư viện

Mở Terminal/CMD và gõ:

```bash
pip install flask flask-cors tensorflow numpy scikit-learn markupsafe
```

### ⚠️ Lưu ý QUAN TRỌNG

Hệ thống yêu cầu phải có sẵn **3 file mô hình đã được train** nằm ở thư mục:

```
D:\AI\clawweb\model\
├── deep_learning_agent_core.keras
├── tokenizer.pkl
└── label_encoder.pkl
```

**Nếu chưa có**, vui lòng chạy file `projectai.ipynb` trước để đúc mô hình! 

---

## 🚀 2. Khởi Động Trạm Gác AI

Tại thư mục chứa file `webg.py`, anh em chạy lệnh:

```bash
python webg.py
```

### Khi thành công, Terminal sẽ hiện:

```
🛡️ Đang đánh thức AI Trinh Sát...
✅ AI đã thức tỉnh và sẵn sàng kết nối với Frontend!
🌐 AI API Server đang chạy tại http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
```

---

## 📡 3. Tài Liệu API (Dành cho team Frontend)

Web Frontend (React/Vue/Vite đang chạy ở `localhost:5173` hoặc bất kỳ đâu) cần gọi API này **ĐỂ QUÉT DỮ LIỆU** trước khi gửi form (Login, Search, Đăng bài...) lên Server chính.

### Endpoint

```
URL: http://127.0.0.1:5000/search
Method: GET
```

### Parameters

| Tham số | Kiểu | Mô tả |
|---------|------|-------|
| `q` | string | Dữ liệu cần quét |

### 📥 Request mẫu

```bash
curl "http://127.0.0.1:5000/search?q=hello%20world"
```

### 📤 Response mẫu (Khi an toàn - HTTP 200)

```html
<h3>Kết quả tìm kiếm: hello world</h3>
<p>Website xử lý an toàn vì AI xác nhận không có mã độc.</p>
```

### 🚨 Response mẫu (Khi phát hiện mã độc - HTTP 403)

```json
{
    "error": "Access Denied by AI WAF",
    "reason": "Detected SQLi",
    "confidence": "98.50%"
}
```

---

## 💻 4. Code Mẫu Tích Hợp Vào Frontend

### Javascript / Vanilla

Anh em copy đoạn code này vào xử lý sự kiện `onSubmit` của Form:

```javascript
// Hàm quét dữ liệu với AI
async function checkInputWithAI(userInput) {
    try {
        const response = await fetch('http://127.0.0.1:5000/search?q=' + encodeURIComponent(userInput), {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Nếu status 403 = phát hiện mã độc
        if (response.status === 403) {
            const result = await response.json();
            // TẠI ĐÂY: Dừng ngay mọi hành động, hiện cảnh báo đỏ lòm cho User!
            alert(`⛔ CẢNH BÁO TỪ TƯỜNG LỬA AI!\nPhát hiện: ${result.reason}\nĐộ tự tin: ${result.confidence}`);
            return false; // Chặn không cho gửi
        }
        
        // Nếu status 200 = an toàn
        return true;
    } catch (error) {
        console.error("Lỗi kết nối tới Trạm Gác AI:", error);
        // Fallback: Tùy dự án, nếu AI sập thì cho qua hoặc chặn cứng
        return true;
    }
}

// Hàm xử lý Submit Form
async function handleFormSubmit(event) {
    event.preventDefault();
    
    // Lấy dữ liệu người dùng gõ
    const inputValue = document.getElementById('myInput').value;
    
    // 1. Mang đi hỏi Trạm Gác AI trước
    const isSafe = await checkInputWithAI(inputValue);
    
    // 2. Nếu an toàn mới cho gọi API thật của Web Server
    if (isSafe) {
        console.log("✅ Dữ liệu sạch! Tiến hành gọi API lưu vào Database...");
        // Gọi axios.post(...) ở đây
        // axios.post('http://yourserver.com/api/save', { data: inputValue })
    }
}

// Gắn sự kiện lên form
document.getElementById('myForm').addEventListener('submit', handleFormSubmit);
```

### React Hook

```javascript
import { useState } from 'react';

function SearchComponent() {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const checkWithAI = async (userInput) => {
        setIsLoading(true);
        try {
            const response = await fetch(
                `http://127.0.0.1:5000/search?q=${encodeURIComponent(userInput)}`
            );
            
            if (response.status === 403) {
                const result = await response.json();
                alert(`⛔ ${result.reason} (${result.confidence})`);
                setIsLoading(false);
                return false;
            }
            
            // Thành công - tiếp tục xử lý
            console.log("✅ Dữ liệu an toàn!");
            setIsLoading(false);
            return true;
        } catch (error) {
            console.error("Lỗi:", error);
            setIsLoading(false);
            return false;
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const isSafe = await checkWithAI(input);
        
        if (isSafe) {
            // Gửi dữ liệu lên server
            console.log("Gửi:", input);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <input 
                value={input} 
                onChange={(e) => setInput(e.target.value)}
                placeholder="Nhập dữ liệu..."
            />
            <button type="submit" disabled={isLoading}>
                {isLoading ? 'Đang kiểm tra...' : 'Tìm kiếm'}
            </button>
        </form>
    );
}

export default SearchComponent;
```

---

## 🧠 5. Cơ chế Ngưỡng Tự Tin (Confidence Threshold)

### Tại sao cần Threshold?

Để tránh việc AI "giết nhầm hơn bỏ sót" chặn oan người dùng thật.

### Cách hoạt động

Hệ thống được cài đặt **Ngưỡng tự tin là 75%**:

| Trường hợp | Kết quả | Hành động |
|-----------|--------|----------|
| AI phát hiện mã độc với độ chắc chắn **≥ 75%** | ❌ Phát hiện | Khóa mõm ngay (HTTP 403) |
| AI nghi ngờ nhưng độ chắc chắn **< 75%** | ✅ Thả qua | In cảnh báo mềm ở Terminal |

### Điều chỉnh Threshold

Sửa file `webg.py`, dòng 21:

```python
# Chặt hơn (bắt mọi thứ ngờ vực)
CONFIDENCE_THRESHOLD = 60.0  

# Lỏng hơn (chỉ chặn khi rất chắc chắn)
CONFIDENCE_THRESHOLD = 85.0  

# Mặc định (cân bằng)
CONFIDENCE_THRESHOLD = 75.0
```

---

## 🛠️ 6. Troubleshooting

### ❌ Lỗi: `ModuleNotFoundError: No module named 'flask'`

**Giải pháp**: Cài đặt Flask
```bash
pip install flask markupsafe
```

### ❌ Lỗi: `FileNotFoundError` cho model files

**Giải pháp**: 
1. Kiểm tra model files tồn tại ở `D:\AI\clawweb\model\`
2. Nếu không, chạy `projectai.ipynb` để train model

### ❌ Lỗi: Port 5000 đã được sử dụng

**Giải pháp**: Đổi port trong `webg.py`
```python
app.run(port=8000)  # Thay 5000 bằng 8000
```

### ❌ False Positives quá cao

**Giải pháp**: Tăng threshold
```python
CONFIDENCE_THRESHOLD = 80.0  # Từ 75.0 lên 80.0
```

---

## 📊 7. Monitoring Logs

### Xem logs trong Terminal

```
2026-03-25 10:31:20 - INFO - ✅ AI đã thức tỉnh
2026-03-25 10:31:25 - WARNING - 🚨 XSS detected (Hash: a1b2c3d4, Confidence: 97.1%)
2026-03-25 10:31:30 - INFO - ⚠️ Low confidence threat: SQLi (65.0%)
```

### Lưu logs vào file

Thêm vào `webg.py` sau dòng `logger = logging.getLogger(__name__)`:

```python
handler = logging.FileHandler('waf.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
```

---

## ✨ 8. Best Practices

### ✅ DO

- ✅ Quét **mọi input từ user** trước khi xử lý
- ✅ Hiện **feedback rõ ràng** nếu bị chặn
- ✅ Log toàn bộ **sự cố bảo mật**
- ✅ **Cập nhật model** định kỳ
- ✅ Kiểm tra **connection** khi khởi động app

### ❌ DON'T

- ❌ Không **bỏ qua WAF** vì "nhanh hơn"
- ❌ Không **trust người dùng** 100%
- ❌ Không **disable HTML escaping**
- ❌ Không **hardcode threshold**

---

## 🎯 Tóm Tắt Quick Start

```bash
# 1. Cài đặt
pip install flask tensorflow numpy scikit-learn markupsafe

# 2. Khởi động
cd D:\AI\clawweb
python webg.py

# 3. Test
curl "http://127.0.0.1:5000/search?q=hello"

# 4. Frontend gọi API
fetch('http://127.0.0.1:5000/search?q=' + userInput)
```

---

## 📞 Liên Hệ & Support

- 📁 **Thư mục chứa model**: `D:\AI\clawweb\model\`
- 📁 **Thư mục tài liệu**: `D:\AI\clawweb\tongquat\`
- 📝 **Config file**: `webg.py`

---

**Chúc anh em code vui vẻ và không bị hack! 🚀**

*Last updated: 25/03/2026*
d:\AI\clawweb\venv311\Scripts\python.exe d:/AI/clawweb/webg.py
