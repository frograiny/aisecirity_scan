# Báo Cáo Xử Lý Lỗi Overfitting & Nhận Diện Sai URL (False Positives)
27/3
## 1. Vấn đề gặp phải (Gây lỗi như thế nào?)
Trong quá trình huấn luyện mô hình AI WAF (Bi-LSTM), chúng ta đã gặp phải hai vấn đề chính:
1. **Mô hình bị Overfitting và nhận diện nhầm URL sạch thành mã độc (SSRF/XSS):** 
   - Nguyên nhân đầu tiên là do chúng ta đã "bơm" quá liều lượng dữ liệu URL sạch (1000 mẫu lặp lại từ 5 URL gốc). Việc chèn quá nhiều dữ liệu lặp lại khiến mô hình học thuộc lòng (memorize) thay vì tổng quát hóa (generalize), dẫn đến Overfitting.
   - Nguyên nhân thứ hai đến từ việc sử dụng `class_weight` mặc định nguyên bản. Đối với các lớp thiểu số (như SSRF bị thiếu data), trọng số (weight) bị đẩy lên quá cao (ví dụ: 400). Điều này ép mô hình phải "sợ" việc đoán sai lớp SSRF, dẫn đến hậu quả là nó cực kỳ nhạy cảm và đánh dấu bừa các URL bình thường thành SSRF hoặc XSS để tránh bị phạt lỗi (tăng mạnh False Positives).
2. **Lỗi `NameError: name 'early_stop' is not defined`:**
   - Xảy ra khi chạy hàm `model.fit()`. Do biến `early_stop` trước đó được khai báo bên trong một hàm (scope cục bộ), nên khi chạy tập lệnh ở cell ngoài cùng (global scope), Python không tìm thấy định nghĩa của biến này.

## 2. Những kỹ thuật đã áp dụng để khắc phục
Để giải quyết bài toán trên, các bước sau đã được lập trình lại vào file `projectai.ipynb`:

### Bước 1: Giảm liều lượng "Kháng thể URL"
- **Hành động:** Thay vì nhân bản 200 lần (1000 mẫu) các URL sạch, hệ thống đã được giảm xuống mức nhân bản 10 lần (chỉ còn 50 mẫu).
- **Mục đích:** Cung cấp cho AI đủ "kháng thể" để nhận biết hình thái của một URL hợp lệ (có `http://`, `https://`, `.com`, `?id=`), nhưng không đủ nhiều để làm lu mờ các dữ liệu Normal khác hoặc gây nhiễu trọng số.

### Bước 2: Cân bằng trọng số mượt mà (Smoothed Class Weights)
- **Hành động:** Thay vì vứt bỏ hoàn toàn `class_weight` (có nguy cơ làm AI lờ đi lớp dữ liệu ít như SSRF), chúng ta áp dụng phép toán Căn bậc 2 (`np.sqrt`) lên trọng số nguyên bản sinh ra từ sklearn.
- **Mục đích:** Kỹ thuật "Làm trơn" (Smoothing) sẽ kéo các trọng số cực đoan (ví dụ: 400) xuống mức ôn hòa hơn (ví dụ: căn bậc hai của 400 là 20). Điều này vừa đủ để AI quan tâm đến các lớp dữ liệu hiếm, nhưng không gây áp lực quá lớn khiến nó mắc chứng "hoang tưởng" (False Positives).

### Bước 3: Sắp xếp lại khai báo biến cục bộ
- **Hành động:** Import thư viện `EarlyStopping` và định nghĩa trực tiếp lại biến `early_stop` ngay bên trong Cell trước khi huấn luyện. Bật lại `class_weight=class_weights_dict` trong cấu hình `model.fit()`.

## 3. Kết quả mong đợi sau khi khắc phục
- **Độ chính xác thực tế (Recall & Precision) cân bằng hơn:** Mô hình không còn đoán bừa URL là SSRF/XSS, giảm thiểu triệt để tình trạng chặn nhầm người dùng hợp lệ (False Positive).
- **Hội tụ ổn định (Stable Convergence):** Đồ thị Loss phân bổ mượt mà hơn, không bị nhảy vọt (spike) do trọng số của loss function không bị phạt quá gắt ở các batch ngẫu nhiên.
- **Tính trơn tru của Pipeline:** Người dùng có thể nhấn "Run All" toàn bộ file `projectai.ipynb` mà không vấp phải các lỗi runtime (như NameError) nữa. Lõi AI đã sẵn sàng để tích hợp vào `webg.py`.
