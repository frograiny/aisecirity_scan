from flask import Flask, request, jsonify
from flask_cors import CORS
from markupsafe import escape
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle
import os
import logging
import hashlib
import time

# ===== SETUP LOGGING =====
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ===== CONFIG =====
MODEL_DIR = r"D:\AI\clawweb\model"
MAX_LEN = 150
CONFIDENCE_THRESHOLD = 75.0

try:
    model = tf.keras.models.load_model(os.path.join(MODEL_DIR, 'deep_learning_agent_core.keras'))
    with open(os.path.join(MODEL_DIR, 'tokenizer.pkl'), 'rb') as f:
        tokenizer = pickle.load(f)
    with open(os.path.join(MODEL_DIR, 'label_encoder.pkl'), 'rb') as f:
        le = pickle.load(f)
    logger.info("✅ AI đã thức tỉnh và sẵn sàng bảo vệ Web!")
except Exception as e:
    logger.error(f"❌ Lỗi: Không tìm thấy não AI. Chi tiết: {e}")
    exit(1)

# ===== SCAN FUNCTION (OPTIMIZED) =====
def scan_payload(payload):
    """Scan payload with AI model"""
    if not payload or (isinstance(payload, str) and payload.strip() == ""):
        return "Normal", 100.0
    
    try:
        seq = tokenizer.texts_to_sequences([str(payload)])
        pad = pad_sequences(seq, maxlen=MAX_LEN, padding='post', truncating='post')
        pred_probs = model.predict(pad, verbose=0)[0]
        
        pred_class = np.argmax(pred_probs)
        label = le.inverse_transform([pred_class])[0]
        confidence = float(pred_probs[pred_class]) * 100
        return label, confidence
    except Exception as e:
        logger.error(f"Error scanning payload: {e}")
        return "Unknown", 0.0

# ===== MIDDLEWARE (FIREWALL) =====
@app.before_request
def firewall_middleware():
    """Check all inputs before request reaches handler"""
    inputs_to_check = []
    inputs_to_check.extend(request.args.values())
    if request.is_json and request.json:
        inputs_to_check.extend(str(v) for v in request.json.values() if v)
    elif request.form:
        inputs_to_check.extend(request.form.values())
    
    for payload in inputs_to_check:
        if not payload or not str(payload).strip():
            continue
        
        label, confidence = scan_payload(payload)
        
        if label != "Normal" and confidence >= CONFIDENCE_THRESHOLD:
            payload_hash = hashlib.sha256(str(payload).encode()).hexdigest()[:8]
            logger.warning(f"🚨 {label} detected (Hash: {payload_hash}, Confidence: {confidence:.1f}%)")
            return jsonify({
                "error": "Access Denied by AI WAF",
                "reason": f"Detected {label}",
                "confidence": f"{confidence:.2f}%"
            }), 403
        elif label != "Normal" and confidence >= 50:
            logger.info(f"⚠️ Low confidence threat: {label} ({confidence:.1f}%)")

# ===== WEB ROUTES =====
@app.route('/')
def home():
    return """
    <h1>🛡️ Website An Toàn - Protected by AI WAF</h1>
    <p>Hệ thống được bảo vệ bởi AI Trinh Sát (Bi-LSTM)</p>
    <p><a href="/search?q=hello">Try search</a></p>
    <p style="color:red; font-weight:bold;">Cảnh báo: Các tấn công sẽ bị chặn!</p>
    """

@app.route('/search', methods=['GET', 'POST'])
def search():
    # GET method (backward compatibility)
    if request.method == 'GET':
        query = request.args.get('q', '')
    # POST method (for URLs with special chars)
    else:
        data = request.get_json() or {}
        query = data.get('q', '')
    
    safe_query = escape(query)
    return f"<h3>Kết quả tìm kiếm: {safe_query}</h3><p>Website xử lý an toàn vì AI xác nhận không có mã độc.</p>"

if __name__ == '__main__':
    logger.info("🌐 Đang khởi động Web Server tại http://127.0.0.1:5000")
    app.run(debug=False, port=5000, threaded=True)