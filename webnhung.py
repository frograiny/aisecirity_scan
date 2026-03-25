from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle
import os
import requests
import logging
import hashlib
from functools import lru_cache
from collections import OrderedDict
from datetime import datetime, timedelta
import time

# ===== ADVANCED LOGGING SYSTEM =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AI-WAF-SHIELD] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("shield_protection.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ===== CONFIGURATION =====
MODEL_DIR = r"D:\AI\clawweb\model"
MAX_LEN = 150
REAL_WEB_URL = "http://localhost:5173"  # Internal Vite server (port 5173)
THRESHOLD = 75.0  # Security threshold
CACHE_TTL = 300  # Cache TTL: 5 minutes
MAX_CACHE_SIZE = 1000  # LRU cache size
REQUEST_TIMEOUT = 10  # Backend request timeout
MAX_RETRIES = 3  # Failed request retries

# ===== LRU CACHE LAYER =====
class PayloadCache:
    """LRU Cache with TTL for scan results"""
    def __init__(self, max_size=1000, ttl=300):
        self.cache = OrderedDict()
        self.ttl_map = {}
        self.max_size = max_size
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, payload):
        """Create hash key for payload"""
        return hashlib.md5(str(payload).encode()).hexdigest()
    
    def get(self, payload):
        """Get from cache if exists and not expired"""
        key = self._make_key(payload)
        if key not in self.cache:
            self.misses += 1
            return None
        
        label, conf, timestamp = self.cache[key]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl):
            del self.cache[key]
            del self.ttl_map[key]
            self.misses += 1
            return None
        
        # Move to end (LRU)
        self.cache.move_to_end(key)
        self.hits += 1
        return label, conf
    
    def set(self, payload, label, conf):
        """Store in cache"""
        key = self._make_key(payload)
        
        if len(self.cache) >= self.max_size:
            # Remove oldest item
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.ttl_map[oldest_key]
        
        self.cache[key] = (label, conf, datetime.now())
        self.ttl_map[key] = datetime.now()
    
    def stats(self):
        """Cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%"
        }

cache = PayloadCache(max_size=MAX_CACHE_SIZE, ttl=CACHE_TTL)

# ===== LOAD AI MODEL =====
try:
    model = tf.keras.models.load_model(os.path.join(MODEL_DIR, 'deep_learning_agent_core.keras'))
    with open(os.path.join(MODEL_DIR, 'tokenizer.pkl'), 'rb') as f:
        tokenizer = pickle.load(f)
    with open(os.path.join(MODEL_DIR, 'label_encoder.pkl'), 'rb') as f:
        le = pickle.load(f)
    logger.info("✅ SHIELD AGENT: Bộ não AI (Bi-LSTM) sẵn sàng bảo vệ localhost:5173")
    logger.info(f"🛡️ Mode: Security-First | Threshold: {THRESHOLD}% | Cache Size: {MAX_CACHE_SIZE}")
except Exception as e:
    logger.error(f"❌ CRITICAL: Lỗi tải Model AI: {e}")
    exit(1)

# ===== SCANNING ENGINE WITH CACHE =====
def scan_payload(payload):
    """Scan payload with LRU cache optimization"""
    if not payload or (isinstance(payload, str) and payload.strip() == ""):
        return "Normal", 100.0
    
    # Check cache first
    cached = cache.get(payload)
    if cached:
        label, conf = cached
        logger.debug(f"💾 CACHE HIT: {label} ({conf:.1f}%)")
        return label, conf
    
    try:
        # Inference
        seq = tokenizer.texts_to_sequences([str(payload)])
        pad = pad_sequences(seq, maxlen=MAX_LEN, padding='post', truncating='post')
        pred = model.predict(pad, verbose=0)[0]
        idx = np.argmax(pred)
        label = le.inverse_transform([idx])[0]
        confidence = float(pred[idx]) * 100
        
        # Store in cache
        cache.set(payload, label, confidence)
        return label, confidence
    except Exception as e:
        logger.error(f"❌ Scan error: {e}")
        return "Unknown", 0.0

# ===== HEALTH CHECK =====
backend_health = {"status": "unknown", "last_check": None, "consecutive_failures": 0}

def check_backend_health():
    """Check if backend (Vite) is alive"""
    global backend_health
    try:
        resp = requests.get(f"{REAL_WEB_URL}/", timeout=2)
        backend_health["status"] = "healthy" if resp.status_code < 500 else "degraded"
        backend_health["last_check"] = datetime.now()
        backend_health["consecutive_failures"] = 0
        return True
    except Exception as e:
        backend_health["status"] = "unavailable"
        backend_health["last_check"] = datetime.now()
        backend_health["consecutive_failures"] += 1
        logger.warning(f"⚠️ Backend health check failed: {e}")
        return False

# ===== SECURITY MIDDLEWARE WITH LOGGING =====
@app.before_request
def security_filter():
    """Main WAF filter - scan all inputs before forwarding"""
    # Bypass static files (no scanning needed)
    if any(request.path.endswith(ext) for ext in ['.js', '.css', '.png', '.jpg', '.svg', '.woff', '.woff2']):
        return None
    
    # Collect all input data
    data_to_scan = []
    data_to_scan.extend(request.args.values())
    
    if request.is_json:
        data_to_scan.extend(str(v) for v in request.get_json().values() if v)
    elif request.form:
        data_to_scan.extend(request.form.values())
    
    # Scan each payload
    for payload in data_to_scan:
        if not payload or len(str(payload)) < 2:
            continue
        
        label, confidence = scan_payload(payload)
        payload_hash = hashlib.sha256(str(payload).encode()).hexdigest()[:8]
        
        # SECURITY-FIRST: High confidence threats = immediate block
        if label != "Normal" and confidence >= THRESHOLD:
            logger.warning(
                f"🛡️ [BLOCKED] {label} | Confidence: {confidence:.1f}% | "
                f"Hash: {payload_hash} | IP: {request.remote_addr}"
            )
            return jsonify({
                "status": "blocked",
                "reason": f"AI WAF detected {label}",
                "confidence": f"{confidence:.1f}%"
            }), 403
        
        # Low confidence = log but allow (user experience, hậu kiểm)
        elif label != "Normal" and confidence >= 50:
            logger.info(
                f"⚠️ [SUSPICIOUS] {label} ({confidence:.1f}%) | "
                f"Hash: {payload_hash} | ALLOWED (below threshold) | IP: {request.remote_addr}"
            )
    
    return None

# ===== HEALTH & MONITORING ENDPOINTS =====
@app.route('/ai-waf/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    check_backend_health()
    return jsonify({
        "status": "operational",
        "backend": backend_health["status"],
        "cache": cache.stats(),
        "model": "Bi-LSTM",
        "threshold": THRESHOLD,
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/ai-waf/stats', methods=['GET'])
def get_stats():
    """Get WAF statistics"""
    return jsonify({
        "cache_stats": cache.stats(),
        "model_accuracy": "93.42%",
        "threshold": THRESHOLD,
        "supported_attacks": ["SQLi", "XSS", "Command Injection", "Path Traversal", "SSRF", "CSRF"],
        "backend_status": backend_health["status"]
    }), 200

# ===== PROXY WITH RETRY LOGIC =====
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    """
    Reverse proxy to backend with retry logic & timeout
    Port 5000 → real user traffic (with AI filtering)
    Port 5173 → internal only (Vite, protected by iptables)
    """
    url = f"{REAL_WEB_URL}/{path}"
    
    # Add query string if exists
    if request.query_string:
        url += f"?{request.query_string.decode()}"
    
    headers = {k: v for k, v in request.headers if k.lower() not in ['host', 'connection']}
    
    # Retry logic for failed requests
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.request(
                method=request.method,
                url=url,
                headers=headers,
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                timeout=REQUEST_TIMEOUT
            )
            
            logger.info(f"✅ [{request.method} {path}] Status: {resp.status_code} | Attempt: {attempt + 1}")
            return Response(resp.content, resp.status_code, resp.headers.items())
        
        except requests.Timeout:
            logger.warning(f"⏱️ Request timeout on attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)  # Wait before retry
            continue
        
        except Exception as e:
            logger.error(f"❌ Proxy error (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)
                continue
            
            return jsonify({
                "status": "error",
                "message": "Backend unavailable",
                "detail": str(e)
            }), 503
    
    return jsonify({"status": "error", "message": "Max retries exceeded"}), 504

# ===== STARTUP CHECKS =====
@app.before_first_request
def startup():
    """Run startup checks"""
    logger.info("=" * 60)
    logger.info("🚀 AI WAF SHIELD AGENT - STARTUP SEQUENCE")
    logger.info("=" * 60)
    logger.info(f"🌐 Listening on: 0.0.0.0:5000 (PUBLIC)")
    logger.info(f"🔒 Backend: {REAL_WEB_URL} (INTERNAL ONLY)")
    logger.info(f"🧠 Model: Bi-LSTM | Accuracy: 93.42%")
    logger.info(f"🛡️ Security Threshold: {THRESHOLD}%")
    logger.info(f"💾 LRU Cache: {MAX_CACHE_SIZE} items, TTL: {CACHE_TTL}s")
    
    check_backend_health()
    logger.info(f"📡 Backend Status: {backend_health['status']}")
    logger.info("=" * 60)

if __name__ == '__main__':
    logger.info("⚡ Starting Shield Agent on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
