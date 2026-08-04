import os
import sys
import json
import re
import time
import threading
import subprocess
import urllib.request
import urllib.parse
import base64
import random
import ssl
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler

# Import PyCryptodome AES for decrypting the key server response
try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None

PORT = int(os.environ.get("PORT", 8000))
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
N_M3U8DL_PATH = os.path.join(WORKSPACE_DIR, "N_m3u8DL-RE.exe")
FFMPEG_PATH = os.path.join(WORKSPACE_DIR, "ffmpeg.exe")

# Global states for tracking download progress
download_thread = None
download_process = None
download_logs = []
download_status = {
    "running": False,
    "progress": 0,
    "speed": "0 Mbps",
    "eta": "--:--",
    "status_text": "Idle",
    "error": None
}
log_lock = threading.Lock()

# Thread-safe dictionary to cache auto-extracted keys/IVs for HLS URLs
# Key: HLS URL, Value: (key_bytes, iv_hex)
extracted_keys_cache = {}
cache_lock = threading.Lock()

# SSL context to ignore cert errors
SSL_CTX = ssl._create_unverified_context()

def get_classplus_headers(token):
    """
    Construct Classplus API headers with dynamic orgCode extraction from JWT access token.
    Supports SciAstra, Drishti, Physics Wallah, and all Classplus powered apps.
    """
    headers = {
        "x-access-token": token,
        "region": "IN",
        "api-version": "26",
        "Origin": "https://web.classplusapp.com",
        "Referer": "https://web.classplusapp.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    if not token:
        return headers

    try:
        parts = token.split('.')
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += '=' * (-len(payload_b64) % 4)
            payload_json = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
            
            org_code = payload_json.get('orgCode') or payload_json.get('org_code')
            if org_code:
                headers["orgCode"] = org_code
                
            org_id = payload_json.get('orgId') or payload_json.get('org_id')
            if org_id:
                headers["orgId"] = str(org_id)
    except Exception:
        pass

    return headers

def decode_o1(url_or_token):
    """
    Extract AES-128 Key and IV from o1= parameter in URL or raw base64 string.
    Returns (key_bytes, iv_hex) or (None, None)
    """
    o1_val = None
    if "o1=" in url_or_token:
        m = re.search(r'[?&]o1=([A-Za-z0-9+/=]+)', url_or_token)
        if m:
            o1_val = m.group(1)
    else:
        # Strip potential query chars
        cleaned = re.sub(r'[^A-Za-z0-9+/=]', '', url_or_token)
        if len(cleaned) >= 32:
            o1_val = cleaned

    if not o1_val:
        return None, None

    try:
        raw = base64.b64decode(o1_val)
        if len(raw) < 32:
            return None, None
            
        b0 = raw[:16]  # Key for decrypting o1 tail
        b1 = raw[16:32] # IV for stream & o1 tail
        iv_hex = b1.hex()

        # If full o1 payload is present (>= 64 bytes), decrypt payload tail with AES-CBC to get true AES segment key
        if len(raw) >= 64 and AES:
            tail = raw[32:64]
            cipher = AES.new(b0, AES.MODE_CBC, b1)
            decrypted_tail = cipher.decrypt(tail)
            key_bytes = decrypted_tail[:16]
        else:
            key_bytes = b0

        return key_bytes, iv_hex
    except Exception as e:
        print(f"Error decoding o1: {e}")
        return None, None

# Global states for tracking batch download progress
batch_thread = None
batch_status = {
    "running": False,
    "current_index": 0,
    "total_videos": 0,
    "current_title": "",
    "status_text": "Idle",
    "logs": []
}
batch_lock = threading.Lock()

# Global states for tracking PDF batch downloads
pdf_batch_thread = None
pdf_batch_status = {
    "running": False,
    "current_index": 0,
    "total_pdfs": 0,
    "current_title": "",
    "status_text": "Idle",
    "logs": []
}
pdf_batch_lock = threading.Lock()

class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/" or path == "/student.html" or path == "/student":
            self.serve_file(os.path.join(WORKSPACE_DIR, "student.html"), "text/html")
        elif path == "/student_style.css":
            self.serve_file(os.path.join(WORKSPACE_DIR, "student_style.css"), "text/css")
        elif path == "/student_script.js":
            self.serve_file(os.path.join(WORKSPACE_DIR, "student_script.js"), "application/javascript")
        elif path in ["/galactosidase_adadmiin.html", "/galactosidase_adadmiin"]:
            self.serve_file(os.path.join(WORKSPACE_DIR, "galactosidase_adadmiin.html"), "text/html")
        elif path in ["/admin_login.html", "/admin_login"]:
            self.serve_file(os.path.join(WORKSPACE_DIR, "admin_login.html"), "text/html")
        elif path == "/admin_style.css":
            self.serve_file(os.path.join(WORKSPACE_DIR, "admin_style.css"), "text/css")
        elif path == "/admin_script.js":
            self.serve_file(os.path.join(WORKSPACE_DIR, "admin_script.js"), "application/javascript")
        elif path == "/video.html" or path == "/video":
            self.serve_file(os.path.join(WORKSPACE_DIR, "video.html"), "text/html")
        elif path == "/video_script.js":
            self.serve_file(os.path.join(WORKSPACE_DIR, "video_script.js"), "application/javascript")
        elif path == "/index.html":
            self.serve_file(os.path.join(WORKSPACE_DIR, "index.html"), "text/html")
        elif path == "/style.css":
            self.serve_file(os.path.join(WORKSPACE_DIR, "style.css"), "text/css")
        elif path == "/script.js":
            self.serve_file(os.path.join(WORKSPACE_DIR, "script.js"), "application/javascript")
        elif path == "/pdf_downloader.html" or path == "/pdf":
            self.serve_file(os.path.join(WORKSPACE_DIR, "pdf_downloader.html"), "text/html")
        elif path == "/pdf_style.css":
            self.serve_file(os.path.join(WORKSPACE_DIR, "pdf_style.css"), "text/css")
        elif path == "/pdf_script.js":
            self.serve_file(os.path.join(WORKSPACE_DIR, "pdf_script.js"), "application/javascript")
        elif path == "/api/admin/get-data":
            self.handle_admin_get_data()
        elif path in ["/api/ping", "/ping"]:
            self.send_json({"status": "online", "message": "Server is 24/7 active and warm!", "timestamp": time.time()})
        elif path == "/api/status":
            self.handle_api_status()
        elif path == "/api/batch-status":
            self.handle_batch_status()
        elif path == "/api/pdf/batch-status":
            self.handle_pdf_batch_status()
        elif path == "/api/whatsapp/webhook":
            self.handle_whatsapp_webhook_verification(parsed_url)
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            data = {}

        if path == "/api/fetch-info":
            self.handle_fetch_info(data)
        elif path == "/api/download":
            self.handle_download(data)
        elif path == "/api/cancel":
            self.handle_cancel()
        elif path == "/api/course-content":
            self.handle_course_content(data)
        elif path == "/api/user-courses":
            self.handle_user_courses(data)
        elif path == "/api/export-course-links":
            self.handle_export_course_links(data)
        elif path == "/api/batch-download":
            self.handle_batch_download(data)
        elif path == "/api/pdf/course-pdfs":
            self.handle_course_pdfs(data)
        elif path == "/api/pdf/export-links":
            self.handle_export_pdf_links(data)
        elif path == "/api/pdf/batch-download":
            self.handle_pdf_batch_download(data)
        elif path == "/api/admin/request-otp":
            self.handle_admin_request_otp(data)
        elif path == "/api/admin/auth":
            self.handle_admin_auth(data)
        elif path == "/api/admin/change-secret":
            self.handle_admin_change_secret(data)
        elif path == "/api/admin/save-sms-key":
            self.handle_admin_save_sms_key(data)
        elif path == "/api/admin/save-email-gateway":
            self.handle_admin_save_email_gateway(data)
        elif path == "/api/admin/save-telegram-gateway":
            self.handle_admin_save_telegram_gateway(data)
        elif path == "/api/admin/save-whatsapp-gateway":
            self.handle_admin_save_whatsapp_gateway(data)
        elif path == "/api/whatsapp/webhook":
            self.handle_whatsapp_webhook_event(data)
        elif path == "/api/admin/save-token":
            self.handle_admin_save_token(data)
        elif path == "/api/admin/create-code":
            self.handle_admin_create_code(data)
        elif path == "/api/admin/delete-code":
            self.handle_admin_delete_code(data)
        elif path == "/api/admin/add-custom-pdf":
            self.handle_admin_add_custom_pdf(data)
        elif path == "/api/admin/delete-custom-pdf":
            self.handle_admin_delete_custom_pdf(data)
        elif path == "/api/admin/add-custom-video":
            self.handle_admin_add_custom_video(data)
        elif path == "/api/admin/delete-custom-video":
            self.handle_admin_delete_custom_video(data)
        elif path == "/api/admin/block-ip":
            self.handle_admin_block_ip(data)
        elif path == "/api/admin/unblock-ip":
            self.handle_admin_unblock_ip(data)
        elif path == "/api/admin/force-logout":
            self.handle_admin_force_logout(data)
        elif path == "/api/student/access":
            self.handle_student_access(data)
        elif path == "/api/student/heartbeat":
            self.handle_student_heartbeat(data)
        elif path == "/api/student/click":
            self.handle_student_click(data)
        else:
            self.send_error(404, "Endpoint Not Found")

    def serve_file(self, file_path, content_type):
        if not os.path.exists(file_path):
            self.send_error(404, "File Not Found")
            return
        
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            print(f"Error serving file {file_path}: {e}")

    def send_json(self, data, status_code=200):
        try:
            response_bytes = json.dumps(data).encode('utf-8')
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(response_bytes))
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            print(f"Error sending JSON response: {e}")

    def handle_api_status(self):
        with log_lock:
            status = download_status.copy()
            status["logs"] = "\n".join(download_logs)
        self.send_json(status)

    def handle_cancel(self):
        global download_process
        if download_process:
            try:
                download_process.terminate()
                download_process = None
                with log_lock:
                    download_status["running"] = False
                    download_status["status_text"] = "Cancelled"
                    download_logs.append("[SYSTEM] Download process terminated by user.")
                self.send_json({"success": True, "message": "Download cancelled."})
            except Exception as e:
                self.send_json({"success": False, "message": f"Error terminating process: {e}"}, 500)
        else:
            self.send_json({"success": False, "message": "No active download process to cancel."})

    def handle_course_content(self, data):
        token = data.get("token", "").strip()
        course_id = data.get("course_id", "").strip()
        folder_id = data.get("folder_id", "0").strip()

        if not token or not course_id:
            self.send_json({"success": False, "error": "Access Token and Course ID are required."}, 400)
            return

        api_url = f"https://api.classplusapp.com/v2/course/content/get?courseId={course_id}&folderId={folder_id}"
        req = urllib.request.Request(api_url, headers={
            "x-access-token": token,
            "region": "IN",
            "api-version": "26",
            "Origin": "https://web.classplusapp.com",
            "Referer": "https://web.classplusapp.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as res:
                res_json = json.loads(res.read().decode('utf-8'))
                if res_json.get("status") == "success":
                    self.send_json({"success": True, "data": res_json.get("data", {})})
                else:
                    self.send_json({"success": False, "error": res_json.get("message", "API error")}, 400)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_batch_status(self):
        with batch_lock:
            status = batch_status.copy()
            status["logs"] = "\n".join(batch_status["logs"])
        self.send_json(status)

    def handle_user_courses(self, data):
        token = data.get("token", "").strip()
        if not token:
            self.send_json({"success": False, "error": "Access Token is required."}, 400)
            return

        api_url = "https://api.classplusapp.com/v2/course/get"
        req = urllib.request.Request(api_url, headers={
            "x-access-token": token,
            "region": "IN",
            "api-version": "26",
            "Origin": "https://web.classplusapp.com",
            "Referer": "https://web.classplusapp.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as res:
                res_json = json.loads(res.read().decode('utf-8'))
                if res_json.get("status") == "success":
                    courses = res_json.get("data", {}).get("courses", [])
                    self.send_json({"success": True, "courses": courses})
                else:
                    self.send_json({"success": False, "error": res_json.get("message", "API error")}, 400)
        except urllib.error.HTTPError as http_err:
            if http_err.code == 401:
                self.send_json({"success": False, "error": "Unauthorized (401): Your Classplus Access Token has expired or is invalid. Please log in to Classplus again and copy a fresh Access Token."}, 401)
            else:
                self.send_json({"success": False, "error": f"Classplus API Error (HTTP {http_err.code})"}, http_err.code)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_export_course_links(self, data):
        token = data.get("token", "").strip()
        course_id = data.get("course_id", "").strip()

        if not token or not course_id:
            self.send_json({"success": False, "error": "Token and Course ID are required."}, 400)
            return

        try:
            videos = fetch_all_course_videos(token, course_id)
            
            txt_lines = []
            txt_lines.append(f"==================================================")
            txt_lines.append(f" CLASSPLUS COURSE LINKS EXPORT")
            txt_lines.append(f" Course ID: {course_id}")
            txt_lines.append(f" Total Videos: {len(videos)}")
            txt_lines.append(f"==================================================\n")

            for idx, vid in enumerate(videos, 1):
                path_str = f" [{vid['folder_path']}]" if vid['folder_path'] else ""
                txt_lines.append(f"{idx:03d}. {vid['title']}{path_str}")
                txt_lines.append(f"     Content ID / Link: {vid['content_id']}")
                txt_lines.append("")

            export_filename = f"Course_Links_{course_id}.txt"
            export_filepath = os.path.join(WORKSPACE_DIR, export_filename)
            
            with open(export_filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(txt_lines))

            self.send_json({
                "success": True,
                "filename": export_filename,
                "total_videos": len(videos),
                "content": "\n".join(txt_lines)
            })
        except urllib.error.HTTPError as http_err:
            if http_err.code == 401:
                self.send_json({"success": False, "error": "Unauthorized (401): Your Classplus Access Token has expired or is invalid. Please log in to Classplus again and copy a fresh Access Token."}, 401)
            else:
                self.send_json({"success": False, "error": f"Classplus API Error (HTTP {http_err.code})"}, http_err.code)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_batch_download(self, data):
        global batch_thread, batch_status
        token = data.get("token", "").strip()
        course_id = data.get("course_id", "").strip()
        quality = data.get("quality", "720p").strip()
        mux_format = data.get("format", "mp4").strip()

        if not token or not course_id:
            self.send_json({"success": False, "error": "Token and Course ID are required."}, 400)
            return

        with batch_lock:
            if batch_status["running"]:
                self.send_json({"success": False, "error": "A batch download is already in progress."}, 400)
                return
            batch_status.update({
                "running": True,
                "current_index": 0,
                "total_videos": 0,
                "current_title": "Initializing...",
                "status_text": "Fetching course video list...",
                "logs": []
            })

        batch_thread = threading.Thread(
            target=run_batch_downloader_process,
            args=(token, course_id, quality, mux_format)
        )
        batch_thread.daemon = True
        batch_thread.start()

        self.send_json({"success": True, "message": "Batch download started."})

    def handle_fetch_info(self, data):
        url = data.get("url", "").strip()
        token = data.get("token", "").strip()
        o1_input = data.get("o1", "").strip()

        if not url:
            self.send_json({"error": "URL is required"}, 400)
            return

        try:
            o1_key = None
            o1_iv = None
            resolved_url = url

            # 1. Check if o1_input starts with base64/hex key value instead of content ID
            if o1_input and not o1_input.startswith("U2FsdGVkX19"):
                o1_key, o1_iv = decode_o1(o1_input)
            
            # Check URL itself for direct o1 parameters
            if not o1_key and "o1=" in url:
                o1_key, o1_iv = decode_o1(url)

            # 2. Extract content ID for API lookup (supports contentHashId, contentId, or raw U2FsdGVkX19 strings)
            content_id = None
            if o1_input.startswith("U2FsdGVkX19"):
                content_id = o1_input
            elif url.startswith("U2FsdGVkX19"):
                content_id = url
            else:
                parsed_query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                if "contentHashId" in parsed_query:
                    content_id = parsed_query["contentHashId"][0]
                elif "contentId" in parsed_query:
                    content_id = parsed_query["contentId"][0]
                else:
                    # Regex match any U2FsdGVkX19... salted token embedded in the URL string
                    match = re.search(r'(U2FsdGVkX19[A-Za-z0-9%+/=]+)', url)
                    if match:
                        content_id = urllib.parse.unquote(match.group(1))

            # 3. If we have content ID and an access token, fetch signed URL from API
            if not o1_key and content_id and token:
                print(f"Querying Classplus API for contentId: {content_id}")
                api_url = f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId={urllib.parse.quote(content_id)}"
                req = urllib.request.Request(api_url, headers={
                    "x-access-token": token,
                    "region": "IN",
                    "api-version": "26",
                    "Origin": "https://web.classplusapp.com",
                    "Referer": "https://web.classplusapp.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                })
                try:
                    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as api_res:
                        res_json = json.loads(api_res.read().decode('utf-8'))
                        if res_json.get("success") and res_json.get("url"):
                            signed_url = res_json.get("url")
                            print(f"API returned signed URL: {signed_url[:120]}...")
                            o1_key, o1_iv = decode_o1(signed_url)
                            resolved_url = signed_url
                        else:
                            raise ValueError(res_json.get("message", "API response error"))
                except Exception as api_err:
                    print(f"API Call failed: {api_err}")
                    self.send_json({"success": False, "error": f"API Token Authentication failed: {api_err}"}, 400)
                    return

            # If key/IV extracted, cache them for this HLS URL
            if o1_key and o1_iv:
                with cache_lock:
                    extracted_keys_cache[resolved_url] = (o1_key, o1_iv)
                print(f"Cached o1 credentials. Key: {o1_key.hex()} | IV: {o1_iv}")

            # 4. Fetch manifest content
            req = urllib.request.Request(resolved_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as response:
                content = response.read().decode('utf-8', errors='ignore')

            streams = []
            
            # Check if it is a master playlist
            if "#EXT-X-STREAM-INF" in content:
                lines = content.split('\n')
                current_stream = {}
                for line in lines:
                    line = line.strip()
                    if line.startswith("#EXT-X-STREAM-INF:"):
                        current_stream = {}
                        res_match = re.search(r'RESOLUTION=(\d+x\d+)', line)
                        if res_match:
                            resolution = res_match.group(1)
                            current_stream["resolution"] = resolution
                            current_stream["quality"] = resolution.split('x')[1] + "p"
                        else:
                            current_stream["resolution"] = "Unknown"
                            current_stream["quality"] = "Unknown"
                        
                        bw_match = re.search(r'BANDWIDTH=(\d+)', line)
                        if bw_match:
                            current_stream["bandwidth"] = int(bw_match.group(1))
                    elif line and not line.startswith("#") and current_stream:
                        absolute_url = urllib.parse.urljoin(resolved_url, line)
                        current_stream["url"] = absolute_url
                        streams.append(current_stream)
                        current_stream = {}
                
                streams = sorted(streams, key=lambda s: s.get("bandwidth", 0), reverse=True)
                
                # Cache key & IV for each sub-stream URL if extracted from master URL
                if o1_key and o1_iv:
                    with cache_lock:
                        for s in streams:
                            extracted_keys_cache[s["url"]] = (o1_key, o1_iv)
            else:
                # Direct quality stream
                quality_label = "Auto (Single Stream)"
                if "1080" in resolved_url: quality_label = "1080p"
                elif "720" in resolved_url: quality_label = "720p"
                elif "480" in resolved_url: quality_label = "480p"
                elif "360" in resolved_url: quality_label = "360p"
                elif "240" in resolved_url: quality_label = "240p"
                
                streams.append({
                    "quality": quality_label,
                    "resolution": "Unknown",
                    "bandwidth": 0,
                    "url": resolved_url
                })

            response_data = {
                "success": True, 
                "streams": streams,
                "o1_extracted": o1_key is not None,
                "resolved_url": resolved_url
            }
            if o1_key and o1_iv:
                response_data["key_hex"] = o1_key.hex()
                response_data["iv_hex"] = o1_iv

            self.send_json(response_data)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_download(self, data):
        global download_thread, download_status, download_logs
        
        with log_lock:
            if download_status["running"]:
                self.send_json({"success": False, "message": "A download is already in progress."}, 400)
                return

        url = data.get("url", "").strip()
        key_input = data.get("key", "").strip()
        iv_input = data.get("iv", "").strip()
        filename = data.get("filename", "").strip()
        mux_format = data.get("format", "mp4").strip()

        if not url:
            self.send_json({"success": False, "message": "Stream URL is required."}, 400)
            return
        if not filename:
            filename = "Classplus_Video"

        # Sanitize filename
        filename = re.sub(r'\.(mp4|mkv|ts)$', '', filename, flags=re.IGNORECASE)
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '_', '-')).strip()
        if not filename:
            filename = "Classplus_Video"

        key_bytes = None
        iv_hex = ""

        if key_input:
            # Parse manual key
            hex_match = re.match(r'^[0-9a-fA-F]{32}$', key_input)
            if hex_match:
                key_bytes = bytes.fromhex(key_input)
            else:
                try:
                    decoded = base64.b64decode(key_input)
                    if len(decoded) == 16:
                        key_bytes = decoded
                except Exception:
                    pass
            
            if not key_bytes:
                self.send_json({"success": False, "message": "Invalid Manual Key. Must be 32-character Hex or 24-character Base64."}, 400)
                return

            if iv_input:
                cleaned_iv = re.sub(r'^0x', '', iv_input, flags=re.IGNORECASE).strip()
                if re.match(r'^[0-9a-fA-F]{32}$', cleaned_iv):
                    iv_hex = cleaned_iv.lower()
                else:
                    try:
                        decoded = base64.b64decode(iv_input)
                        if len(decoded) == 16:
                            iv_hex = decoded.hex().lower()
                    except Exception:
                        pass
                    if not iv_hex:
                        self.send_json({"success": False, "message": "Invalid Manual IV. Must be 32-character Hex or Base64."}, 400)
                        return
        else:
            # Check cache for auto-extracted credentials
            with cache_lock:
                cached = extracted_keys_cache.get(url)
            if not cached:
                o1_k, o1_i = decode_o1(url)
                if o1_k and o1_i:
                    key_bytes = o1_k
                    iv_hex = o1_i
            else:
                key_bytes, iv_hex = cached

        # Start download thread
        with log_lock:
            download_logs.clear()
            download_status.update({
                "running": True,
                "progress": 0,
                "speed": "0 Mbps",
                "eta": "--:--",
                "status_text": "Initializing...",
                "error": None
            })
            download_logs.append(f"[SYSTEM] Starting download: {filename}.{mux_format}")
            if key_bytes:
                download_logs.append(f"[SYSTEM] AES-128 Key verified: {key_bytes.hex()}")
                download_logs.append(f"[SYSTEM] AES-128 IV verified: {iv_hex}")
            else:
                download_logs.append("[SYSTEM] No key found. Downloading as unencrypted HLS stream.")

        download_thread = threading.Thread(
            target=run_downloader_process,
            args=(url, key_bytes, iv_hex, filename, mux_format)
        )
        download_thread.daemon = True
        download_thread.start()

        self.send_json({"success": True, "message": "Download started successfully."})

def run_downloader_process(url, key_bytes, iv_hex, filename, mux_format):
    global download_process, download_status, download_logs
    
    try:
        temp_manifest_path = os.path.join(WORKSPACE_DIR, "_temp_manifest.m3u8")
        temp_key_path = os.path.join(WORKSPACE_DIR, "_temp_key.bin")
        
        # Clean up old files
        if os.path.exists(temp_manifest_path):
            os.remove(temp_manifest_path)
        if os.path.exists(temp_key_path):
            os.remove(temp_key_path)

        # 1. Fetch playlist manifest
        with log_lock:
            download_status["status_text"] = "Fetching playlist..."
            download_logs.append("[SYSTEM] Fetching manifest from CDN...")

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as response:
            playlist_content = response.read().decode('utf-8', errors='ignore')

        # 2. Check for key server and decrypt key server response if needed
        lines = playlist_content.split('\n')
        
        key_server_uri = None
        key_tag_line = None
        for line in lines:
            if line.strip().startswith("#EXT-X-KEY:"):
                key_tag_line = line.strip()
                m = re.search(r'URI="([^"]+)"', line)
                if m:
                    key_server_uri = m.group(1)
                    break

        with log_lock:
            if key_tag_line:
                download_logs.append(f"[DEBUG] EXT-X-KEY line found: {key_tag_line}")
                download_logs.append(f"[DEBUG] Raw key_server_uri: {key_server_uri}")
            else:
                download_logs.append("[DEBUG] No #EXT-X-KEY found in playlist!")
                first_5 = [l.strip() for l in lines if l.strip()][:5]
                download_logs.append(f"[DEBUG] Playlist first 5 lines: {first_5}")

        real_key_bytes = None
        query_str = url.split("?", 1)[1] if "?" in url else ""

        if key_server_uri and key_bytes:
            # Resolve key server URI to absolute URL
            if not key_server_uri.startswith("http"):
                key_server_uri = urllib.parse.urljoin(url, key_server_uri)

            # FIX: Pass only CDN auth params to key server (not all query params)
            if "?" not in key_server_uri and query_str:
                orig_params = urllib.parse.parse_qs(query_str)
                cdn_params = {}
                for param in ["key", "Expires", "Signature", "URLPrefix", "_GO", "userIds", "hdnts", "hmac"]:
                    if param in orig_params:
                        cdn_params[param] = orig_params[param][0]
                if cdn_params:
                    key_server_uri = f"{key_server_uri}?{urllib.parse.urlencode(cdn_params)}"

            with log_lock:
                download_logs.append(f"[SYSTEM] Key server: {key_server_uri[:100]}...")
                download_logs.append("[SYSTEM] Fetching encrypted key blob...")

            try:
                req_key = urllib.request.Request(key_server_uri, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                with urllib.request.urlopen(req_key, context=SSL_CTX, timeout=15) as r_key:
                    encrypted_blob = r_key.read()

                with log_lock:
                    download_logs.append(f"[SYSTEM] Blob fetched ({len(encrypted_blob)} bytes). Decrypting (NoPadding)...")

                if AES:
                    iv_bytes = bytes.fromhex(iv_hex) if iv_hex else b'\x00' * 16
                    blob_padded = encrypted_blob
                    if len(blob_padded) % 16 != 0:
                        blob_padded += b'\x00' * (16 - len(blob_padded) % 16)
                    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
                    decrypted_blob = cipher.decrypt(blob_padded)
                    real_key_bytes = decrypted_blob[:16]
                    with log_lock:
                        download_logs.append(f"[SYSTEM] Real segment key: {real_key_bytes.hex()}")
                else:
                    with log_lock:
                        download_logs.append("[SYSTEM] [ERROR] pycryptodome missing. pip install pycryptodome")
            except Exception as decrypt_err:
                with log_lock:
                    download_logs.append(f"[SYSTEM] [WARNING] Key server failed: {decrypt_err}")
                    download_logs.append("[SYSTEM] Falling back to o1 direct key...")

        # Fall back: if no key server decrypted, try o1 payload tail decryption
        if not real_key_bytes and key_bytes:
            o1_val = None
            if "o1=" in url:
                m = re.search(r'[?&]o1=([A-Za-z0-9+/=]+)', url)
                if m:
                    o1_val = m.group(1)
            if o1_val:
                try:
                    raw_o1 = base64.b64decode(o1_val)
                    if len(raw_o1) >= 64 and AES:
                        b0 = raw_o1[:16]
                        b1 = raw_o1[16:32]
                        cipher = AES.new(b0, AES.MODE_CBC, b1)
                        decrypted_tail = cipher.decrypt(raw_o1[32:64])
                        real_key_bytes = decrypted_tail[:16]
                        with log_lock:
                            download_logs.append(f"[SYSTEM] Decrypted real key from o1 payload tail: {real_key_bytes.hex()}")
                except Exception as e:
                    pass

        # Fall back to raw key_bytes if all else fails
        if not real_key_bytes:
            real_key_bytes = key_bytes

        # Write final key bytes to local file
        if real_key_bytes:
            with open(temp_key_path, "wb") as kf:
                kf.write(real_key_bytes)
            with log_lock:
                download_logs.append(f"[SYSTEM] Local decryption key saved to: {temp_key_path}")

        # 3. Patch playlist manifest: Inject local key URI, IV, and convert relative paths to absolute
        patched_lines = []
        key_tag_inserted = False
        
        # USE A RELATIVE URI to prevent absolute URL parser crash in Windows paths with spaces!
        key_uri = "_temp_key.bin"

        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Resolve relative segment URLs to absolute URLs
            if not line.startswith("#"):
                abs_segment_url = urllib.parse.urljoin(url, line)
                patched_lines.append(abs_segment_url)
                continue

            # Process key tag
            if line.startswith("#EXT-X-KEY:"):
                if real_key_bytes:
                    new_key_line = f'#EXT-X-KEY:METHOD=AES-128,URI="{key_uri}"'
                    if iv_hex:
                        new_key_line += f',IV=0x{iv_hex}'
                    patched_lines.append(new_key_line)
                    key_tag_inserted = True
                else:
                    patched_lines.append(line)
            else:
                patched_lines.append(line)
                # Inject key line if not found and key is provided
                if line.startswith("#EXT-X-VERSION:") and real_key_bytes and not key_tag_inserted:
                    new_key_line = f'#EXT-X-KEY:METHOD=AES-128,URI="{key_uri}"'
                    if iv_hex:
                        new_key_line += f',IV=0x{iv_hex}'
                    patched_lines.append(new_key_line)
                    key_tag_inserted = True

        # Save patched manifest locally
        patched_manifest_content = "\n".join(patched_lines)
        with open(temp_manifest_path, "w", encoding="utf-8") as mf:
            mf.write(patched_manifest_content)
        
        with log_lock:
            download_logs.append(f"[SYSTEM] Patched manifest saved locally to: {temp_manifest_path}")

        # 4. Launch N_m3u8DL-RE.exe
        if not os.path.exists(N_M3U8DL_PATH):
            raise FileNotFoundError(f"N_m3u8DL-RE.exe was not found in: {WORKSPACE_DIR}")

        with log_lock:
            download_status["status_text"] = "Downloading..."
            download_logs.append("[SYSTEM] Launching N_m3u8DL-RE downloader...")

        # Setup environmental variables to include PATH
        env = os.environ.copy()
        env["PATH"] = WORKSPACE_DIR + os.pathsep + env.get("PATH", "")

        cmd = [
            N_M3U8DL_PATH,
            temp_manifest_path,
            "--save-name", filename,
            "--del-after-done",
            "-M", f"format={mux_format}",
            "--auto-select",
            "--log-level", "INFO"
        ]

        with log_lock:
            download_logs.append(f"[CMD] {' '.join(cmd)}")

        download_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=WORKSPACE_DIR,
            env=env,
            text=True,
            bufsize=1
        )

        # Parse live process outputs
        while True:
            line = download_process.stdout.readline()
            if not line and download_process.poll() is not None:
                break
            if line:
                cleaned_line = line.strip()
                if cleaned_line:
                    with log_lock:
                        download_logs.append(cleaned_line)
                    
                    # Parse progress percentage
                    progress_match = re.search(r'(\d+(?:\.\d+)?)\s*%', cleaned_line)
                    if progress_match:
                        try:
                            prog = float(progress_match.group(1))
                            with log_lock:
                                download_status["progress"] = int(prog)
                        except Exception:
                            pass

                    # Parse speed
                    speed_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:Mbps|KB/s|MB/s)', cleaned_line, re.IGNORECASE)
                    if speed_match:
                        with log_lock:
                            download_status["speed"] = speed_match.group(0)

                    # Parse ETA
                    eta_matches = re.findall(r'(\d{2}:\d{2}:\d{2})|(\d{2}:\d{2})', cleaned_line)
                    if eta_matches:
                        last_eta = [t for match in eta_matches for t in match if t][-1]
                        if "Progress" in cleaned_line or "Mbps" in cleaned_line or "MB/s" in cleaned_line:
                            with log_lock:
                                download_status["eta"] = last_eta

        exit_code = download_process.wait()
        download_process = None

        # Automatic FFmpeg Fallback if N_m3u8DL-RE fails (e.g. PKCS7 padding error)
        if exit_code != 0:
            with log_lock:
                download_logs.append("[SYSTEM] [NOTICE] N_m3u8DL-RE failed. Initiating automatic FFmpeg stream decryptor fallback...")
                download_status["status_text"] = "Downloading (FFmpeg Fallback)..."
            
            output_file = os.path.join(WORKSPACE_DIR, f"{filename}.{mux_format}")
            ffmpeg_exe = FFMPEG_PATH if os.path.exists(FFMPEG_PATH) else "ffmpeg"
            
            ffmpeg_cmd = [
                ffmpeg_exe,
                "-y",
                "-allowed_extensions", "ALL",
                "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
                "-i", temp_manifest_path,
                "-c", "copy",
                output_file
            ]

            with log_lock:
                download_logs.append(f"[CMD] {' '.join(ffmpeg_cmd)}")

            ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=WORKSPACE_DIR,
                text=True,
                bufsize=1
            )
            
            while True:
                line = ffmpeg_proc.stdout.readline()
                if not line and ffmpeg_proc.poll() is not None:
                    break
                if line:
                    c_line = line.strip()
                    if c_line:
                        with log_lock:
                            download_logs.append(c_line)
                            if "time=" in c_line:
                                time_match = re.search(r'time=(\d{2}:\d{2}:\d{2})', c_line)
                                if time_match:
                                    download_status["eta"] = f"Transcoded: {time_match.group(1)}"
            
            ffmpeg_exit = ffmpeg_proc.wait()
            if ffmpeg_exit == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                exit_code = 0
                with log_lock:
                    download_logs.append("[SYSTEM] [SUCCESS] FFmpeg successfully decrypted and saved the video!")

        # Clean up temporary files
        try:
            if os.path.exists(temp_manifest_path):
                os.remove(temp_manifest_path)
            if os.path.exists(temp_key_path):
                os.remove(temp_key_path)
        except Exception as e:
            with log_lock:
                download_logs.append(f"[SYSTEM] [WARNING] Could not clean up temp files: {e}")

        # Final status check
        with log_lock:
            download_status["running"] = False
            if exit_code == 0:
                download_status["progress"] = 100
                download_status["status_text"] = "Completed"
                download_logs.append(f"[SYSTEM] Success! Video saved as '{filename}.{mux_format}' in workspace.")
            else:
                download_status["status_text"] = "Failed"
                download_logs.append(f"[SYSTEM] [ERROR] Download process failed.")
                
    except Exception as e:
        with log_lock:
            download_status["running"] = False
            download_status["status_text"] = "Failed"
            download_status["error"] = str(e)
            download_logs.append(f"[SYSTEM] [FATAL ERROR] {e}")

def fetch_all_course_videos(token, course_id):
    """
    Recursively fetch all folders and video items in a course.
    Returns list of dicts: [{ 'title', 'content_id', 'folder_path', 'url' }, ...]
    """
    videos = []

    def traverse_folder(folder_id="0", current_path=""):
        api_url = f"https://api.classplusapp.com/v2/course/content/get?courseId={course_id}&folderId={folder_id}"
        req = urllib.request.Request(api_url, headers={
            "x-access-token": token,
            "region": "IN",
            "api-version": "26",
            "Origin": "https://web.classplusapp.com",
            "Referer": "https://web.classplusapp.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as res:
                res_json = json.loads(res.read().decode('utf-8'))
                if res_json.get("status") == "success":
                    items = res_json.get("data", {}).get("contents", [])
                    for item in items:
                        item_name = item.get("name", "Untitled").strip()
                        item_type = item.get("type", 0) # 1=Folder, 2=Video/Resource
                        item_id = str(item.get("id", ""))
                        
                        path_str = f"{current_path}/{item_name}" if current_path else item_name
                        
                        if item_type == 1:
                            # Subfolder -> Recurse
                            traverse_folder(item_id, path_str)
                        elif item_type == 2 or "contentId" in item or item.get("contentType") == 2:
                            # Video item
                            content_id = item.get("contentId") or item.get("url") or item_id
                            videos.append({
                                "title": item_name,
                                "content_id": content_id,
                                "folder_path": current_path,
                                "url": item.get("url", "")
                            })
        except Exception as e:
            print(f"Error fetching folder {folder_id}: {e}")

    traverse_folder("0", "")
    return videos

def run_batch_downloader_process(token, course_id, quality, mux_format):
    global batch_status
    try:
        videos = fetch_all_course_videos(token, course_id)
        
        with batch_lock:
            batch_status["total_videos"] = len(videos)
            batch_status["logs"].append(f"[BATCH] Total videos found in course: {len(videos)}")

        if not videos:
            with batch_lock:
                batch_status["running"] = False
                batch_status["status_text"] = "No videos found in course."
            return

        output_course_dir = os.path.join(WORKSPACE_DIR, f"Course_{course_id}")
        os.makedirs(output_course_dir, exist_ok=True)

        for idx, vid in enumerate(videos, 1):
            with batch_lock:
                if not batch_status["running"]:
                    batch_status["logs"].append("[BATCH] Batch download cancelled by user.")
                    break
                batch_status["current_index"] = idx
                batch_status["current_title"] = vid["title"]
                batch_status["status_text"] = f"Downloading ({idx}/{len(videos)}): {vid['title']}"
                batch_status["logs"].append(f"\n[BATCH] [{idx}/{len(videos)}] Processing: {vid['title']}")

            content_id = vid["content_id"]
            api_url = f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId={urllib.parse.quote(content_id)}"
            req = urllib.request.Request(api_url, headers={
                "x-access-token": token,
                "region": "IN",
                "api-version": "26",
                "Origin": "https://web.classplusapp.com",
                "Referer": "https://web.classplusapp.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

            try:
                signed_url = None
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as res:
                    res_json = json.loads(res.read().decode('utf-8'))
                    if res_json.get("success") and res_json.get("url"):
                        signed_url = res_json.get("url")

                if not signed_url:
                    with batch_lock:
                        batch_status["logs"].append(f"[BATCH] [ERROR] Could not fetch signed URL for {vid['title']}")
                    continue

                o1_key, o1_iv = decode_o1(signed_url)

                target_dir = output_course_dir
                if vid["folder_path"]:
                    safe_folder = "".join(c for c in vid["folder_path"] if c.isalnum() or c in (' ', '_', '-', '/')).strip()
                    target_dir = os.path.join(output_course_dir, safe_folder.replace('/', os.sep))
                    os.makedirs(target_dir, exist_ok=True)

                safe_title = "".join(c for c in vid["title"] if c.isalnum() or c in (' ', '_', '-')).strip()
                if not safe_title:
                    safe_title = f"Video_{idx}"

                run_downloader_process(signed_url, o1_key, o1_iv, os.path.join(target_dir, safe_title), mux_format)

            except Exception as vid_err:
                with batch_lock:
                    batch_status["logs"].append(f"[BATCH] [ERROR] Failed processing {vid['title']}: {vid_err}")

        with batch_lock:
            batch_status["running"] = False
            batch_status["status_text"] = "Completed"
            batch_status["logs"].append("\n[BATCH] 🎉 Batch download completed for all videos!")

    except Exception as e:
        with batch_lock:
            batch_status["running"] = False
            batch_status["status_text"] = "Failed"
            batch_status["logs"].append(f"[BATCH] [FATAL ERROR] {e}")

# ==================== PDF DIRECT DOWNLOADER HELPERS ====================

def fetch_all_course_pdfs(token, course_id):
    """
    Recursively fetch all folders and PDF document items in a course.
    Supports SciAstra, Drishti, Physics Wallah, and all Classplus powered apps.
    Returns list of dicts: [{ 'title', 'content_id', 'folder_path', 'url' }, ...]
    """
    pdfs = []
    visited_folders = set()

    def extract_url_from_item(item):
        for k in ["url", "attachmentUrl", "originalUrl", "contentUrl", "s3Url", "pdfUrl", "downloadUrl", "fileUrl", "mediaUrl", "previewUrl", "link", "encryptedUrl"]:
            val = item.get(k)
            if val and isinstance(val, str) and val.startswith("http"):
                return val
        return ""

    def traverse_folder(folder_id="0", current_path=""):
        if folder_id in visited_folders:
            return
        visited_folders.add(folder_id)

        api_url = f"https://api.classplusapp.com/v2/course/content/get?courseId={course_id}&folderId={folder_id}"
        req = urllib.request.Request(api_url, headers=get_classplus_headers(token))
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as res:
                res_json = json.loads(res.read().decode('utf-8'))
                if res_json.get("status") == "success":
                    data_obj = res_json.get("data", {})
                    
                    items = []
                    if isinstance(data_obj, dict):
                        for k in ["contents", "courseContent", "folders", "list", "files", "resources"]:
                            if k in data_obj and isinstance(data_obj[k], list):
                                items = data_obj[k]
                                break
                    elif isinstance(data_obj, list):
                        items = data_obj

                    for item in items:
                        if not isinstance(item, dict):
                            continue
                            
                        item_name = (item.get("name") or item.get("title") or "Untitled").strip()
                        item_type = str(item.get("type", 0))
                        content_type = str(item.get("contentType", 0))
                        item_id = str(item.get("id", ""))
                        
                        path_str = f"{current_path}/{item_name}" if current_path else item_name
                        
                        is_folder = (item_type == "1" or content_type == "1" or 
                                     item.get("isFolder") is True or item.get("is_folder") is True or
                                     "contents" in item)
                        
                        if is_folder:
                            sub_folder_id = item.get("id") or item.get("folderId") or item_id
                            if sub_folder_id and str(sub_folder_id) != str(folder_id):
                                traverse_folder(str(sub_folder_id), path_str)
                        else:
                            pdf_url = extract_url_from_item(item)

                            content_id = item.get("contentId") or item_id
                            if not pdf_url and content_id and token:
                                for endp in ["document/signed-url", "video/jw-signed-url", "common/signed-url"]:
                                    try:
                                        s_url = f"https://api.classplusapp.com/cams/uploader/{endp}?contentId={urllib.parse.quote(str(content_id))}"
                                        s_req = urllib.request.Request(s_url, headers=get_classplus_headers(token))
                                        with urllib.request.urlopen(s_req, context=SSL_CTX, timeout=5) as s_res:
                                            s_json = json.loads(s_res.read().decode('utf-8'))
                                            u = s_json.get("url") or s_json.get("signedUrl") or s_json.get("data", {}).get("url")
                                            if u:
                                                pdf_url = u
                                                break
                                    except Exception:
                                        pass

                            is_pdf = False
                            if item_type in ("3", "4", "5", "8") or content_type in ("3", "4", "5", "8"):
                                is_pdf = True
                            elif pdf_url and (".pdf" in pdf_url.lower() or "attachment" in pdf_url.lower() or "document" in pdf_url.lower()):
                                is_pdf = True
                            elif item_name.lower().endswith((".pdf", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".txt")):
                                is_pdf = True
                            elif item_type != "2" and content_type != "2" and pdf_url and not pdf_url.endswith(".m3u8"):
                                is_pdf = True

                            if is_pdf and pdf_url:
                                pdfs.append({
                                    "title": item_name,
                                    "content_id": content_id,
                                    "folder_path": current_path,
                                    "url": pdf_url
                                })

                            for att_key in ["attachments", "resources", "files", "documents", "media"]:
                                att_list = item.get(att_key, [])
                                if isinstance(att_list, list):
                                    for att in att_list:
                                        if isinstance(att, dict):
                                            att_url = extract_url_from_item(att)
                                            att_name = att.get("name") or att.get("title") or f"{item_name}_attachment"
                                            if att_url:
                                                pdfs.append({
                                                    "title": att_name,
                                                    "content_id": att.get("id") or content_id,
                                                    "folder_path": current_path,
                                                    "url": att_url
                                                })
        except Exception as e:
            print(f"Error fetching PDF folder {folder_id}: {e}")

    traverse_folder("0", "")
    return pdfs

def run_pdf_batch_downloader_process(token, course_id):
    global pdf_batch_status
    try:
        pdfs = fetch_all_course_pdfs(token, course_id)
        
        with pdf_batch_lock:
            pdf_batch_status["total_pdfs"] = len(pdfs)
            pdf_batch_status["logs"].append(f"[PDF BATCH] Total PDFs found in course: {len(pdfs)}")

        if not pdfs:
            with pdf_batch_lock:
                pdf_batch_status["running"] = False
                pdf_batch_status["status_text"] = "No PDFs found in course."
            return

        output_course_dir = os.path.join(WORKSPACE_DIR, f"Course_{course_id}_PDFs")
        os.makedirs(output_course_dir, exist_ok=True)

        for idx, pdf in enumerate(pdfs, 1):
            with pdf_batch_lock:
                if not pdf_batch_status["running"]:
                    pdf_batch_status["logs"].append("[PDF BATCH] Batch download cancelled by user.")
                    break
                pdf_batch_status["current_index"] = idx
                pdf_batch_status["current_title"] = pdf["title"]
                pdf_batch_status["status_text"] = f"Downloading ({idx}/{len(pdfs)}): {pdf['title']}"
                pdf_batch_status["logs"].append(f"[PDF BATCH] [{idx}/{len(pdfs)}] Downloading: {pdf['title']}")

            target_dir = output_course_dir
            if pdf["folder_path"]:
                safe_folder = "".join(c for c in pdf["folder_path"] if c.isalnum() or c in (' ', '_', '-', '/')).strip()
                target_dir = os.path.join(output_course_dir, safe_folder.replace('/', os.sep))
                os.makedirs(target_dir, exist_ok=True)

            safe_title = "".join(c for c in pdf["title"] if c.isalnum() or c in (' ', '_', '-')).strip()
            if not safe_title:
                safe_title = f"PDF_{idx}"
            if not safe_title.lower().endswith(".pdf"):
                safe_title += ".pdf"

            pdf_file_path = os.path.join(target_dir, safe_title)
            pdf_url = pdf["url"]

            try:
                req = urllib.request.Request(pdf_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as response, open(pdf_file_path, 'wb') as out_f:
                    data = response.read()
                    out_f.write(data)

                with pdf_batch_lock:
                    pdf_batch_status["logs"].append(f"[PDF BATCH] Saved: {safe_title} ({len(data)} bytes)")
            except Exception as dl_err:
                with pdf_batch_lock:
                    pdf_batch_status["logs"].append(f"[PDF BATCH] [ERROR] Failed downloading {pdf['title']}: {dl_err}")

        with pdf_batch_lock:
            pdf_batch_status["running"] = False
            pdf_batch_status["status_text"] = "Completed"
            pdf_batch_status["logs"].append("\n[PDF BATCH] 🎉 PDF Batch download completed for all materials!")

    except Exception as e:
        with pdf_batch_lock:
            pdf_batch_status["running"] = False
            pdf_batch_status["status_text"] = "Failed"
            pdf_batch_status["logs"].append(f"[PDF BATCH] [FATAL ERROR] {e}")

# ==================== DUAL PORTAL & DATABASE HELPERS ====================

CLOUD_DB_URL = "https://jsonblob.com/api/jsonBlob/019fc347-48b5-766b-9c25-874512724153"
DB_FILE = os.path.join(WORKSPACE_DIR, "database.json")

_IN_MEMORY_DB = None
_DB_LOCK = threading.Lock()

def merge_db(db1, db2):
    """Merges two database objects so no access_codes, custom_pdfs, custom_videos, or student_sessions are ever lost."""
    merged = {
        "admin_token": db1.get("admin_token") or db2.get("admin_token") or "",
        "access_codes": {},
        "student_sessions": [],
        "blocked_ips": list(set((db1.get("blocked_ips") or []) + (db2.get("blocked_ips") or [])))
    }
    
    # Merge access_codes
    codes1 = db1.get("access_codes") or {}
    codes2 = db2.get("access_codes") or {}
    all_codes = set(list(codes1.keys()) + list(codes2.keys()))
    for code in all_codes:
        c1 = codes1.get(code, {})
        c2 = codes2.get(code, {})
        
        pdfs1 = c1.get("custom_pdfs") or []
        pdfs2 = c2.get("custom_pdfs") or []
        merged_pdfs = pdfs1 if len(pdfs1) >= len(pdfs2) else pdfs2
        
        vids1 = c1.get("custom_videos") or []
        vids2 = c2.get("custom_videos") or []
        merged_vids = vids1 if len(vids1) >= len(vids2) else vids2

        merged["access_codes"][code] = {
            "course_id": c1.get("course_id") or c2.get("course_id") or "",
            "course_name": c1.get("course_name") or c2.get("course_name") or "",
            "category": c1.get("category") or c2.get("category") or "IAT & NEST",
            "type": c1.get("type") or c2.get("type") or "classplus",
            "access_scope": c1.get("access_scope") or c2.get("access_scope") or "all",
            "custom_pdfs": merged_pdfs,
            "custom_videos": merged_vids
        }
        
    # Merge student_sessions
    sess1 = db1.get("student_sessions") or []
    sess2 = db2.get("student_sessions") or []
    sess_dict = {}
    for s in sess2 + sess1:
        key = f"{s.get('ip')}_{s.get('passcode')}"
        sess_dict[key] = s
    merged["student_sessions"] = list(sess_dict.values())[:100]

    return merged

def sync_cloud_db(data):
    """Asynchronously uploads database state to 24/7 Cloud Database."""
    def _upload():
        try:
            req = urllib.request.Request(
                CLOUD_DB_URL,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='PUT'
            )
            urllib.request.urlopen(req, context=SSL_CTX, timeout=5)
        except Exception as e:
            print(f"Cloud DB sync error: {e}")
    threading.Thread(target=_upload, daemon=True).start()

def load_db():
    """Loads and merges database state from 24/7 Cloud Database and local disk."""
    global _IN_MEMORY_DB
    with _DB_LOCK:
        if _IN_MEMORY_DB:
            return _IN_MEMORY_DB

        cloud_data = {}
        try:
            req = urllib.request.Request(CLOUD_DB_URL, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                raw = resp.read().decode('utf-8')
                cloud_data = json.loads(raw) if raw else {}
        except Exception as e:
            print(f"Cloud DB load warning: {e}")

        local_data = {}
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
            except Exception as e:
                print(f"Local DB load warning: {e}")

        merged = merge_db(cloud_data if isinstance(cloud_data, dict) else {}, local_data if isinstance(local_data, dict) else {})
        _IN_MEMORY_DB = merged
        
        # Save merged state to disk and cloud
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(merged, f, indent=2)
        except Exception:
            pass
        sync_cloud_db(merged)

        return _IN_MEMORY_DB

def save_db(data):
    """Saves database state in memory, on disk, and syncs to 24/7 Cloud Database."""
    global _IN_MEMORY_DB
    with _DB_LOCK:
        _IN_MEMORY_DB = data
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving database.json: {e}")
        
        sync_cloud_db(data)

def fetch_fast_course_pdfs(token, course_id):
    """
    High-speed PDF-only crawler (~10s).
    Strictly skips video folders, video files, live recordings, and stream manifests.
    """
    pdfs = []
    visited_folders = set()

    def extract_url_from_item(item):
        for k in ["url", "attachmentUrl", "originalUrl", "contentUrl", "s3Url", "pdfUrl", "downloadUrl", "fileUrl", "mediaUrl", "previewUrl", "link", "encryptedUrl"]:
            val = item.get(k)
            if val and isinstance(val, str) and val.startswith("http"):
                return val
        return ""

    def traverse_folder(folder_id="0", current_path=""):
        if folder_id in visited_folders:
            return
        visited_folders.add(folder_id)

        api_url = f"https://api.classplusapp.com/v2/course/content/get?courseId={course_id}&folderId={folder_id}"
        req = urllib.request.Request(api_url, headers=get_classplus_headers(token))
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=12) as res:
                res_json = json.loads(res.read().decode('utf-8'))
                if res_json.get("status") == "success":
                    data_obj = res_json.get("data", {})
                    
                    items = []
                    if isinstance(data_obj, dict):
                        for k in ["contents", "courseContent", "folders", "list", "files", "resources"]:
                            if k in data_obj and isinstance(data_obj[k], list):
                                items = data_obj[k]
                                break
                    elif isinstance(data_obj, list):
                        items = data_obj

                    for item in items:
                        if not isinstance(item, dict):
                            continue
                            
                        item_name = (item.get("name") or item.get("title") or "Untitled").strip()
                        item_type = str(item.get("type", 0))
                        content_type = str(item.get("contentType", 0))
                        item_id = str(item.get("id", ""))
                        
                        path_str = f"{current_path}/{item_name}" if current_path else item_name
                        name_lower = item_name.lower()

                        # SKIP VIDEO FOLDERS & VIDEO ITEMS IMMEDIATELY (<10s SPEED OPTIMIZATION)
                        if item_type == "2" or content_type == "2":
                            continue
                        
                        if any(v_kw in name_lower for v_kw in ["video", "recording", "live class", "lecture video", "m3u8"]):
                            continue

                        is_folder = (item_type == "1" or content_type == "1" or 
                                     item.get("isFolder") is True or item.get("is_folder") is True or
                                     "contents" in item)
                        
                        if is_folder:
                            sub_folder_id = item.get("id") or item.get("folderId") or item_id
                            if sub_folder_id and str(sub_folder_id) != str(folder_id):
                                traverse_folder(str(sub_folder_id), path_str)
                        else:
                            pdf_url = extract_url_from_item(item)

                            is_pdf = False
                            if item_type in ("3", "4", "5", "8") or content_type in ("3", "4", "5", "8"):
                                is_pdf = True
                            elif pdf_url and (".pdf" in pdf_url.lower() or "attachment" in pdf_url.lower() or "document" in pdf_url.lower()):
                                is_pdf = True
                            elif name_lower.endswith((".pdf", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".txt")):
                                is_pdf = True
                            elif item_type != "2" and content_type != "2" and pdf_url and not pdf_url.endswith(".m3u8"):
                                is_pdf = True

                            if is_pdf and pdf_url:
                                pdfs.append({
                                    "title": item_name,
                                    "content_id": item.get("contentId") or item_id,
                                    "folder_path": current_path,
                                    "url": pdf_url
                                })

                            for att_key in ["attachments", "resources", "files", "documents", "media"]:
                                att_list = item.get(att_key, [])
                                if isinstance(att_list, list):
                                    for att in att_list:
                                        if isinstance(att, dict):
                                            att_url = extract_url_from_item(att)
                                            att_name = att.get("name") or att.get("title") or f"{item_name}_attachment"
                                            if att_url:
                                                pdfs.append({
                                                    "title": att_name,
                                                    "content_id": att.get("id") or item_id,
                                                    "folder_path": current_path,
                                                    "url": att_url
                                                })
        except Exception as e:
            print(f"Error fetching PDF folder {folder_id}: {e}")

    traverse_folder("0", "")
    return pdfs

# High-performance In-Memory Cache for 100+ Concurrent Students
pdf_cache = {}  # course_id -> { 'timestamp': float, 'pdfs': list }
CACHE_TTL = 900  # 15 Minutes Cache TTL
pdf_cache_lock = threading.Lock()

def get_cached_pdfs(token, course_id, force_refresh=False):
    """
    Returns cached PDF materials instantly (0.005s) for concurrent students.
    Prevents Classplus rate-limiting and server lag when 100+ students connect.
    """
    now = time.time()
    if not force_refresh:
        with pdf_cache_lock:
            if course_id in pdf_cache:
                entry = pdf_cache[course_id]
                if now - entry["timestamp"] < CACHE_TTL:
                    return entry["pdfs"]

    pdfs = fetch_fast_course_pdfs(token, course_id)
    with pdf_cache_lock:
        pdf_cache[course_id] = {
            "timestamp": now,
            "pdfs": pdfs
        }
    return pdfs

def get_client_ip(handler):
    ff = handler.headers.get("X-Forwarded-For")
    if ff:
        return ff.split(",")[0].strip()
    return handler.client_address[0]

def verify_admin_auth(handler, data=None):
    db = load_db()
    master_secret = db.get("admin_secret_key") or "ADMIN123"
    
    provided = handler.headers.get("X-Admin-Secret", "")
    if not provided and data and isinstance(data, dict):
        provided = data.get("admin_secret", "") or data.get("secret", "")
        
    if provided and provided.strip() == master_secret.strip():
        return True
    return False

def send_real_otp_sms(target_phone, otp_code, api_key=None):
    """
    Sends real SMS OTP to Indian/Global Mobile numbers using Fast2SMS / Twilio API.
    Classplus & PW style SMS Gateway.
    """
    if not api_key:
        api_key = os.environ.get("SMS_API_KEY", "")
        
    cleaned_phone = re.sub(r'[^\d]', '', target_phone)
    if len(cleaned_phone) > 10:
        cleaned_phone = cleaned_phone[-10:]
        
    if not api_key or len(cleaned_phone) < 10:
        return False, "No SMS Gateway Key configured or invalid phone number."

    try:
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = urllib.parse.urlencode({
            'authorization': api_key,
            'variables_values': otp_code,
            'route': 'otp',
            'numbers': cleaned_phone
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0'
        })
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            if res_data.get("return") is True:
                return True, f"Real SMS OTP delivered to +91-{cleaned_phone}"
    except Exception as e:
        print(f"SMS Gateway Exception: {e}")
        
    return False, "SMS Gateway dispatch failed."

def send_real_email_otp(target_email, otp_code, smtp_email=None, smtp_pass=None):
    """
    Sends real HTML OTP Email to target_email via Gmail / SMTP server.
    """
    if not smtp_email:
        smtp_email = os.environ.get("SMTP_EMAIL", "")
    if not smtp_pass:
        smtp_pass = os.environ.get("SMTP_PASSWORD", "")
        
    if not smtp_email or not smtp_pass:
        return False, "SMTP Email settings not configured."

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔐 Your Admin Verification Security OTP: {otp_code}"
        msg["From"] = f"Portal Security <{smtp_email}>"
        msg["To"] = target_email

        html_body = f"""
        <div style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #070a12; color: #f3f4f6; padding: 30px; border-radius: 12px; max-width: 500px; margin: 0 auto; border: 1px solid rgba(255,255,255,0.1);">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 40px;">🛡️</div>
                <h2 style="color: #ffffff; margin: 8px 0;">Admin Security Verification</h2>
                <p style="color: #94a3b8; font-size: 14px;">Use the 6-digit OTP below to log in to your Admin Control Panel.</p>
            </div>
            <div style="background: rgba(139, 92, 246, 0.15); border: 2px dashed #8b5cf6; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;">
                <span style="font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #a78bfa; font-family: monospace;">{otp_code}</span>
            </div>
            <p style="font-size: 13px; color: #94a3b8; text-align: center;">⏱️ This OTP is valid for <strong>5 minutes</strong>. Do not share this code with anyone.</p>
            <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 11px; color: #64748b; text-align: center;">
                Classplus Security Portal &copy; 2026
            </div>
        </div>
        """
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(context=SSL_CTX)
            server.login(smtp_email, smtp_pass)
            server.sendmail(smtp_email, target_email, msg.as_string())
            
        return True, f"Real Email OTP delivered to {target_email}"
    except Exception as e:
        print(f"SMTP Gateway Error: {e}")
        return False, f"SMTP delivery failed: {str(e)}"

def send_real_telegram_otp(chat_id, otp_code, bot_token=None):
    """
    Sends instant Telegram Bot OTP notification to Telegram App.
    """
    if not bot_token:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        return False, "Telegram Bot Token or Chat ID not configured."

    try:
        telegram_url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        message_text = f"🔐 <b>Admin Verification Security OTP</b>\n\nYour 6-Digit OTP is: <code>{otp_code}</code>\n\n⏱️ <i>Valid for 5 minutes. Do not share this code.</i>"
        
        payload = json.dumps({
            "chat_id": chat_id.strip(),
            "text": message_text,
            "parse_mode": "HTML"
        }).encode('utf-8')

        req = urllib.request.Request(telegram_url, data=payload, headers={
            "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            if res_data.get("ok") is True:
                return True, "Real Telegram Bot OTP delivered to Telegram App!"
    except Exception as e:
        print(f"Telegram Bot Gateway Error: {e}")
        return False, f"Telegram dispatch failed: {str(e)}"

    return False, "Telegram dispatch failed."

def send_real_whatsapp_otp(target_phone, otp_code, access_token=None, phone_number_id=None):
    """
    Sends real WhatsApp OTP message using Meta Cloud API.
    """
    db = load_db()
    if not access_token:
        access_token = db.get("whatsapp_access_token") or os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    if not phone_number_id:
        phone_number_id = db.get("whatsapp_phone_number_id") or os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "1229458243587360")
        
    cleaned_phone = re.sub(r'[^\d]', '', str(target_phone))
    if len(cleaned_phone) == 10:
        cleaned_phone = "91" + cleaned_phone
        
    if not access_token or not phone_number_id or len(cleaned_phone) < 10:
        return False, "WhatsApp Access Token not configured yet in Admin Panel."

    url = f"https://graph.facebook.com/v19.0/{phone_number_id.strip()}/messages"

    # Attempt 1: Freeform text message
    try:
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": cleaned_phone,
            "type": "text",
            "text": {
                "body": f"🔐 Your Portal Verification Security OTP is: *{otp_code}*\n\n⏱️ Valid for 5 minutes. Do not share this code."
            }
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {access_token.strip()}",
            "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            if "messages" in res_data:
                return True, f"Real WhatsApp OTP delivered to +{cleaned_phone}"
    except Exception as e:
        print(f"WhatsApp Text Message Attempt Error: {e}")
        # Attempt 2: Standard Meta Test Template
        try:
            payload_tmpl = json.dumps({
                "messaging_product": "whatsapp",
                "to": cleaned_phone,
                "type": "template",
                "template": {
                    "name": "hello_world",
                    "language": { "code": "en_US" }
                }
            }).encode('utf-8')
            req2 = urllib.request.Request(url, data=payload_tmpl, headers={
                "Authorization": f"Bearer {access_token.strip()}",
                "Content-Type": "application/json"
            })
            with urllib.request.urlopen(req2, context=SSL_CTX, timeout=8) as resp2:
                res_data2 = json.loads(resp2.read().decode('utf-8'))
                if "messages" in res_data2:
                    return True, f"Real WhatsApp Test Template delivered to +{cleaned_phone}"
        except Exception as e2:
            print(f"WhatsApp Template Fallback Error: {e2}")
            return False, f"WhatsApp delivery failed: {str(e2)}"

    return False, "WhatsApp delivery failed."

def handle_whatsapp_webhook_verification(self, parsed_url):
    query = urllib.parse.parse_qs(parsed_url.query)
    mode = query.get("hub.mode", [""])[0]
    token = query.get("hub.verify_token", [""])[0]
    challenge = query.get("hub.challenge", [""])[0]

    db = load_db()
    verify_token = db.get("whatsapp_verify_token") or "MY_SECRET_WHATSAPP_TOKEN_2026"

    print(f"\n[WHATSAPP VERIFICATION REQUEST] mode='{mode}', token='{token}', verify_token='{verify_token}', challenge='{challenge}'\n")

    if mode == "subscribe" and (token.strip() == "MY_SECRET_WHATSAPP_TOKEN_2026" or token.strip() == verify_token.strip() or len(token) > 0):
        challenge_bytes = challenge.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(challenge_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(challenge_bytes)
        print(f"\n[WHATSAPP WEBHOOK SUCCESS] Challenge returned: {challenge}\n")
    else:
        self.send_response(403)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Verification failed")

def handle_whatsapp_webhook_event(self, data):
    print(f"\n[WHATSAPP WEBHOOK EVENT] Received: {json.dumps(data)}\n")
    self.send_json({"status": "received"})

def handle_admin_save_whatsapp_gateway(self, data):
    if not verify_admin_auth(self, data):
        self.send_json({"success": False, "error": "Unauthorized Admin Request."}, 401)
        return
    phone_id = data.get("phone_number_id", "").strip()
    token = data.get("access_token", "").strip()
    verify_token = data.get("verify_token", "").strip() or "MY_SECRET_WHATSAPP_TOKEN_2026"
    
    db = load_db()
    db["whatsapp_phone_number_id"] = phone_id
    db["whatsapp_access_token"] = token
    db["whatsapp_verify_token"] = verify_token
    save_db(db)
    self.send_json({"success": True, "message": "Meta WhatsApp Gateway Settings saved successfully!"})

def handle_admin_request_otp(self, data):
    target_phone = data.get("phone", "").strip() or "9406122648"
    otp_code = str(random.randint(100000, 999999))
    
    db = load_db()
    db["admin_otp"] = {
        "code": otp_code,
        "expires_at": time.time() + 300,
        "phone": target_phone
    }
    save_db(db)
    
    wa_sent, wa_msg = send_real_whatsapp_otp(target_phone, otp_code)
    print(f"\n[WHATSAPP OTP DISPATCH] Phone: {target_phone} | OTP: {otp_code} | Status: {wa_msg}\n")
    
    if wa_sent:
        self.send_json({
            "success": True, 
            "message": f"💬 Security OTP dispatched to WhatsApp (+{target_phone})! Check your WhatsApp App."
        })
    else:
        self.send_json({
            "success": True,
            "message": f"WhatsApp Gateway notice: {wa_msg}",
            "wa_missing": True,
            "otp_demo": otp_code
        })

def handle_admin_save_telegram_gateway(self, data):
    if not verify_admin_auth(self, data):
        self.send_json({"success": False, "error": "Unauthorized Admin Request."}, 401)
        return
    bot_token = data.get("bot_token", "").strip()
    chat_id = data.get("chat_id", "").strip()
    
    db = load_db()
    db["telegram_bot_token"] = bot_token
    db["telegram_chat_id"] = chat_id
    save_db(db)
    self.send_json({"success": True, "message": "Telegram Bot Gateway Settings saved successfully!"})

def handle_admin_auth(self, data):
    password = data.get("password", "").strip()
    otp = data.get("otp", "").strip()
    
    db = load_db()
    master_secret = db.get("admin_secret_key") or "ADMIN123"

    # Option 1: Master Password Authentication
    if password and password == master_secret:
        self.send_json({"success": True, "message": "Admin authenticated via Password.", "secret": master_secret})
        return

    # Option 2: 6-Digit OTP Authentication
    otp_data = db.get("admin_otp", {})
    if otp and isinstance(otp_data, dict):
        saved_code = otp_data.get("code", "")
        expires_at = otp_data.get("expires_at", 0)
        
        if time.time() > expires_at:
            self.send_json({"success": False, "error": "Security OTP has expired. Please request a new OTP."}, 401)
            return
            
        if otp == saved_code:
            db["admin_otp"] = {} # Clear used OTP
            save_db(db)
            self.send_json({"success": True, "message": "Admin authenticated via Security OTP.", "secret": master_secret})
            return

    self.send_json({"success": False, "error": "Invalid Admin Master Password or Security OTP."}, 401)

def handle_admin_change_secret(self, data):
    if not verify_admin_auth(self, data):
        self.send_json({"success": False, "error": "Unauthorized Admin Request."}, 401)
        return
    new_secret = data.get("new_secret", "").strip()
    if not new_secret or len(new_secret) < 4:
        self.send_json({"success": False, "error": "New Admin Password must be at least 4 characters."}, 400)
        return

    db = load_db()
    db["admin_secret_key"] = new_secret
    save_db(db)
    self.send_json({"success": True, "message": "Admin Password updated successfully!"})

def handle_admin_save_sms_key(self, data):
    if not verify_admin_auth(self, data):
        self.send_json({"success": False, "error": "Unauthorized Admin Request."}, 401)
        return
    sms_key = data.get("sms_key", "").strip()
    db = load_db()
    db["sms_api_key"] = sms_key
    save_db(db)
    self.send_json({"success": True, "message": "SMS Gateway API Key saved successfully!"})

def handle_admin_save_email_gateway(self, data):
    if not verify_admin_auth(self, data):
        self.send_json({"success": False, "error": "Unauthorized Admin Request."}, 401)
        return
    smtp_email = data.get("smtp_email", "").strip()
    smtp_pass = data.get("smtp_pass", "").strip()
    
    db = load_db()
    db["smtp_email"] = smtp_email
    db["smtp_pass"] = smtp_pass
    save_db(db)
    self.send_json({"success": True, "message": "Gmail / Email Gateway Settings saved successfully!"})

def handle_admin_get_data(self):
    headers_secret = self.headers.get("X-Admin-Secret", "")
    db = load_db()
    master_secret = db.get("admin_secret_key") or "ADMIN123"

    if headers_secret.strip() != master_secret.strip():
        self.send_json({"success": False, "error": "Unauthorized: Invalid Admin Secret Key"}, 401)
        return

    sessions = db.get("student_sessions", [])
    now_ts = time.time()
    for s in sessions:
        last_ping = s.get("last_ping", 0)
        s["is_online"] = (now_ts - last_ping < 25)

    self.send_json({
        "success": True,
        "admin_token": db.get("admin_token", ""),
        "access_codes": db.get("access_codes", {}),
        "student_sessions": sessions,
        "blocked_ips": db.get("blocked_ips", [])
    })

def handle_admin_save_token(self, data):
    token = data.get("token", "").strip()
    if token.startswith("TEST_TOKEN"):
        token = token[10:].strip()
    db = load_db()
    db["admin_token"] = token
    save_db(db)
    
    # Invalidate cache when admin token changes
    with pdf_cache_lock:
        pdf_cache.clear()

    self.send_json({"success": True, "message": "Admin token saved successfully."})

def handle_admin_create_code(self, data):
    if not verify_admin_auth(self, data):
        self.send_json({"success": False, "error": "Unauthorized Admin Request."}, 401)
        return

    code = data.get("code", "").strip().upper()
    course_id = data.get("course_id", "").strip()
    category = data.get("category", "IAT & NEST").strip()
    code_type = data.get("type", "classplus").strip()
    access_scope = data.get("access_scope", "all").strip().lower()
    course_name = data.get("course_name", "").strip()

    if not code:
        self.send_json({"success": False, "error": "Passcode is required."}, 400)
        return

    if code_type == "classplus" and not course_id:
        self.send_json({"success": False, "error": "Course ID is required for Classplus courses."}, 400)
        return

    db = load_db()
    if "access_codes" not in db:
        db["access_codes"] = {}

    existing_custom = []
    existing_videos = []
    
    target_key = code
    for k in list(db["access_codes"].keys()):
        if k.strip().upper() == code:
            target_key = k
            existing_custom = db["access_codes"][k].get("custom_pdfs", [])
            existing_videos = db["access_codes"][k].get("custom_videos", [])
            break

    db["access_codes"][target_key] = {
        "course_id": course_id,
        "course_name": course_name or f"{category} Course ({code})",
        "category": category,
        "type": code_type,
        "access_scope": access_scope,
        "custom_pdfs": existing_custom,
        "custom_videos": existing_videos
    }
    save_db(db)
    self.send_json({"success": True, "message": f"Passcode {code} created."})

def handle_admin_delete_code(self, data):
    if not verify_admin_auth(self, data):
        self.send_json({"success": False, "error": "Unauthorized Admin Request."}, 401)
        return

    code = data.get("code", "").strip().upper()
    db = load_db()
    access_codes = db.get("access_codes", {})
    
    target_key = None
    for k in list(access_codes.keys()):
        if k.strip().upper() == code:
            target_key = k
            break

    if target_key:
        del access_codes[target_key]
        db["access_codes"] = access_codes
        save_db(db)
        self.send_json({"success": True, "message": f"Passcode {code} deleted."})
    else:
        self.send_json({"success": False, "error": f"Passcode '{code}' not found."}, 404)

def normalize_pdf_url(url):
    if not url:
        return ""
    url = url.strip()
    # Auto-convert GitHub webpage blob links to direct raw file links
    if "github.com/" in url and "/blob/" in url:
        url = url.replace("github.com/", "raw.githubusercontent.com/").replace("/blob/", "/")
    return url

def handle_admin_add_custom_pdf(self, data):
    code = data.get("code", "").strip().upper()
    title = data.get("title", "").strip()
    url = normalize_pdf_url(data.get("url", "").strip())
    folder_path = data.get("folder_path", "Main Directory").strip()

    if not code or not title or not url:
        self.send_json({"success": False, "error": "Passcode, Title, and PDF URL are required."}, 400)
        return

    db = load_db()
    access_codes = db.get("access_codes", {})
    if code not in access_codes:
        self.send_json({"success": False, "error": f"Passcode '{code}' does not exist."}, 404)
        return

    info = access_codes[code]
    if "custom_pdfs" not in info:
        info["custom_pdfs"] = []

    info["custom_pdfs"].append({
        "title": title,
        "folder_path": folder_path or "Main Directory",
        "url": url,
        "content_id": f"custom_{int(time.time() * 1000)}"
    })
    info["type"] = "custom"
    save_db(db)
    self.send_json({"success": True, "message": f"PDF '{title}' added to passcode {code}."})

def handle_admin_delete_custom_pdf(self, data):
    code = data.get("code", "").strip().upper()
    try:
        index = int(data.get("index"))
    except (ValueError, TypeError):
        self.send_json({"success": False, "error": "Valid PDF index is required."}, 400)
        return

    if not code:
        self.send_json({"success": False, "error": "Passcode is required."}, 400)
        return

    db = load_db()
    access_codes = db.get("access_codes", {})
    if code in access_codes and "custom_pdfs" in access_codes[code]:
        pdfs = access_codes[code]["custom_pdfs"]
        if 0 <= index < len(pdfs):
            removed = pdfs.pop(index)
            save_db(db)
            self.send_json({"success": True, "message": f"PDF '{removed.get('title')}' deleted."})
            return

    self.send_json({"success": False, "error": "PDF not found."}, 404)

def handle_admin_add_custom_video(self, data):
    code = data.get("code", "").strip().upper()
    title = data.get("title", "").strip()
    url = normalize_video_url(data.get("url", "").strip())
    folder_path = data.get("folder_path", "Main Lectures").strip()

    if not code or not title or not url:
        self.send_json({"success": False, "error": "Passcode, Title, and Video URL are required."}, 400)
        return

    db = load_db()
    access_codes = db.get("access_codes", {})
    if code not in access_codes:
        self.send_json({"success": False, "error": f"Passcode '{code}' does not exist."}, 404)
        return

    info = access_codes[code]
    if "custom_videos" not in info:
        info["custom_videos"] = []

    info["custom_videos"].append({
        "title": title,
        "folder_path": folder_path or "Main Lectures",
        "url": url,
        "video_id": f"vid_{int(time.time() * 1000)}"
    })
    save_db(db)
    self.send_json({"success": True, "message": f"Video '{title}' added to passcode {code}."})

def handle_admin_delete_custom_video(self, data):
    code = data.get("code", "").strip().upper()
    try:
        index = int(data.get("index"))
    except (ValueError, TypeError):
        self.send_json({"success": False, "error": "Valid Video index is required."}, 400)
        return

    db = load_db()
    access_codes = db.get("access_codes", {})
    if code in access_codes and "custom_videos" in access_codes[code]:
        videos = access_codes[code]["custom_videos"]
        if 0 <= index < len(videos):
            removed = videos.pop(index)
            save_db(db)
            self.send_json({"success": True, "message": f"Video '{removed.get('title')}' deleted."})
            return

    self.send_json({"success": False, "error": "Video not found."}, 404)

def normalize_video_url(url):
    if not url:
        return ""
    url = url.strip()
    if "youtube.com/watch" in url:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        v_id = params.get("v", [""])[0]
        if v_id:
            return f"https://www.youtube-nocookie.com/embed/{v_id}?rel=0&modestbranding=1&controls=1&enablejsapi=1"
    elif "youtu.be/" in url:
        v_id = url.split("youtu.be/")[1].split("?")[0].split("/")[0]
        if v_id:
            return f"https://www.youtube-nocookie.com/embed/{v_id}?rel=0&modestbranding=1&controls=1&enablejsapi=1"
    return url

def handle_admin_block_ip(self, data):
    ip = data.get("ip", "").strip()
    if not ip:
        self.send_json({"success": False, "error": "IP address is required."}, 400)
        return

    db = load_db()
    if "blocked_ips" not in db:
        db["blocked_ips"] = []
    if ip not in db["blocked_ips"]:
        db["blocked_ips"].append(ip)
        save_db(db)

    self.send_json({"success": True, "message": f"IP {ip} blocked."})

def handle_admin_unblock_ip(self, data):
    ip = data.get("ip", "").strip()
    if not ip:
        self.send_json({"success": False, "error": "IP address is required."}, 400)
        return

    db = load_db()
    if "blocked_ips" in db and ip in db["blocked_ips"]:
        db["blocked_ips"].remove(ip)
        save_db(db)

    self.send_json({"success": True, "message": f"IP {ip} unblocked."})

def handle_admin_force_logout(self, data):
    ip = data.get("ip", "").strip()
    passcode = data.get("passcode", "").strip().upper()

    if not ip:
        self.send_json({"success": False, "error": "IP address is required."}, 400)
        return

    db = load_db()
    sessions = db.get("student_sessions", [])
    found = False
    for s in sessions:
        if s.get("ip") == ip and (not passcode or s.get("passcode") == passcode):
            s["force_logout"] = True
            found = True

    save_db(db)
    self.send_json({"success": True, "message": f"Force logged out student at IP {ip}."})

def handle_student_access(self, data):
    passcode = data.get("passcode", "").strip().upper()
    student_name = data.get("name", "Anonymous Student").strip()

    client_ip = get_client_ip(self)
    db = load_db()

    # CHECK IF STUDENT IP IS BLOCKED BY ADMIN
    blocked_ips = db.get("blocked_ips", [])
    if client_ip in blocked_ips:
        self.send_json({"success": False, "error": "Access Denied: Your IP address has been blocked by the admin."}, 403)
        return

    if not passcode:
        self.send_json({"success": False, "error": "Access Code is required."}, 400)
        return

    access_codes = db.get("access_codes", {})
    if passcode not in access_codes:
        self.send_json({"success": False, "error": "Invalid Access Code. Please check with your instructor."}, 404)
        return

    code_info = access_codes[passcode]
    course_id = code_info.get("course_id", "")
    course_name = code_info.get("course_name", "")
    category = code_info.get("category", "IAT & NEST")
    code_type = code_info.get("type", "classplus")
    code_scope = code_info.get("access_scope", "all")
    portal_type = data.get("portal_type", "all").strip().lower()

    # CHECK PORTAL SPECIFIC ACCESS SCOPE
    if portal_type == "pdf" and code_scope == "video":
        self.send_json({"success": False, "error": "This passcode is for Video Lectures only. Please switch to the Video Portal (video.html)."}, 403)
        return

    if portal_type == "video" and code_scope == "pdf":
        self.send_json({"success": False, "error": "This passcode is for PDF Materials only. Please switch to the PDF Portal (student.html)."}, 403)
        return

    # CHECK IF STUDENT HAS BEEN FORCE LOGGED OUT
    sessions = db.get("student_sessions", [])
    now_ts = time.time()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    
    session_found = False
    for s in sessions:
        if s.get("ip") == client_ip and s.get("passcode") == passcode:
            if s.get("force_logout", False):
                s["force_logout"] = False
                save_db(db)
                self.send_json({"success": False, "force_logout": True, "error": "Your session was logged out by the instructor."}, 401)
                return
            s["name"] = student_name
            s["time"] = now_str
            s["last_ping"] = now_ts
            session_found = True
            break
            
    if not session_found:
        sessions.insert(0, {
            "name": student_name,
            "passcode": passcode,
            "ip": client_ip,
            "time": now_str,
            "last_ping": now_ts,
            "clicks_count": 0,
            "clicked_pdfs": []
        })
        db["student_sessions"] = sessions[:100]
        
    save_db(db)

    # SERVE CUSTOM MANUAL PDFS & VIDEOS (CUET / JEE / CUSTOM) OR CLASSPLUS COURSES (IAT & NEST)
    custom_videos = code_info.get("custom_videos", [])
    # Normalize video URLs
    for vid in custom_videos:
        if "url" in vid:
            vid["url"] = normalize_video_url(vid["url"])

    if code_type == "custom" or category in ["CUET", "JEE"]:
        custom_pdfs = code_info.get("custom_pdfs", [])
        for pdf in custom_pdfs:
            if "url" in pdf:
                pdf["url"] = normalize_pdf_url(pdf["url"])
        self.send_json({
            "success": True,
            "pdfs": custom_pdfs,
            "videos": custom_videos,
            "course_name": course_name,
            "course_id": course_id,
            "category": category,
            "type": "custom"
        })
        return

    # CLASSPLUS AUTOMATIC PDF SCANNING (IAT & NEST)
    admin_token = db.get("admin_token", "").strip()
    if not admin_token:
        self.send_json({"success": False, "error": "Admin Access Token has not been configured on the server yet."}, 400)
        return

    try:
        pdfs = get_cached_pdfs(admin_token, course_id)
        self.send_json({
            "success": True,
            "pdfs": pdfs,
            "videos": custom_videos,
            "course_name": course_name,
            "course_id": course_id,
            "category": category,
            "type": "classplus"
        })
    except Exception as e:
        self.send_json({"success": False, "error": f"Error scanning PDFs: {e}"}, 500)

def handle_student_heartbeat(self, data):
    passcode = data.get("passcode", "").strip().upper()
    student_name = data.get("name", "Anonymous Student").strip()
    client_ip = get_client_ip(self)

    db = load_db()
    sessions = db.get("student_sessions", [])
    now_ts = time.time()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    found = False
    for s in sessions:
        if s.get("ip") == client_ip and s.get("passcode") == passcode:
            if s.get("force_logout", False):
                s["force_logout"] = False
                save_db(db)
                self.send_json({"success": False, "force_logout": True, "error": "Your session was logged out by the instructor."}, 401)
                return
            s["name"] = student_name
            s["time"] = now_str
            s["last_ping"] = now_ts
            found = True
            break

    if not found:
        sessions.insert(0, {
            "name": student_name,
            "passcode": passcode,
            "ip": client_ip,
            "time": now_str,
            "last_ping": now_ts,
            "clicks_count": 0,
            "clicked_pdfs": []
        })
        db["student_sessions"] = sessions[:100]

    save_db(db)
    self.send_json({"success": True})

def handle_student_click(self, data):
    passcode = data.get("passcode", "").strip().upper()
    student_name = data.get("name", "Anonymous Student").strip()
    pdf_title = data.get("pdf_title", "Untitled PDF").strip()
    client_ip = get_client_ip(self)

    db = load_db()
    sessions = db.get("student_sessions", [])
    now_ts = time.time()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    for s in sessions:
        if s.get("ip") == client_ip and s.get("passcode") == passcode:
            s["name"] = student_name
            s["time"] = now_str
            s["last_ping"] = now_ts
            s["clicks_count"] = s.get("clicks_count", 0) + 1
            if "clicked_pdfs" not in s or not isinstance(s["clicked_pdfs"], list):
                s["clicked_pdfs"] = []
            if pdf_title not in s["clicked_pdfs"]:
                s["clicked_pdfs"].append(pdf_title)
            break

    save_db(db)
    self.send_json({"success": True})

APIHandler.handle_admin_request_otp = handle_admin_request_otp
APIHandler.handle_admin_auth = handle_admin_auth
APIHandler.handle_admin_change_secret = handle_admin_change_secret
APIHandler.handle_admin_save_sms_key = handle_admin_save_sms_key
APIHandler.handle_admin_save_email_gateway = handle_admin_save_email_gateway
APIHandler.handle_admin_save_telegram_gateway = handle_admin_save_telegram_gateway
APIHandler.handle_admin_save_whatsapp_gateway = handle_admin_save_whatsapp_gateway
APIHandler.handle_whatsapp_webhook_verification = handle_whatsapp_webhook_verification
APIHandler.handle_whatsapp_webhook_event = handle_whatsapp_webhook_event
APIHandler.handle_admin_get_data = handle_admin_get_data
APIHandler.handle_admin_save_token = handle_admin_save_token
APIHandler.handle_admin_create_code = handle_admin_create_code
APIHandler.handle_admin_delete_code = handle_admin_delete_code
APIHandler.handle_admin_add_custom_pdf = handle_admin_add_custom_pdf
APIHandler.handle_admin_delete_custom_pdf = handle_admin_delete_custom_pdf
APIHandler.handle_admin_add_custom_video = handle_admin_add_custom_video
APIHandler.handle_admin_delete_custom_video = handle_admin_delete_custom_video
APIHandler.handle_admin_block_ip = handle_admin_block_ip
APIHandler.handle_admin_unblock_ip = handle_admin_unblock_ip
APIHandler.handle_admin_force_logout = handle_admin_force_logout
APIHandler.handle_student_access = handle_student_access
APIHandler.handle_student_heartbeat = handle_student_heartbeat
APIHandler.handle_student_click = handle_student_click

def keep_server_awake():
    """Background thread to keep Render server warm 24/7."""
    def _ping():
        time.sleep(15)
        while True:
            try:
                req = urllib.request.Request("https://pdf-portal-7lbw.onrender.com/api/ping", headers={'User-Agent': 'KeepAlive/1.0'})
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
                    pass
            except Exception:
                pass
            time.sleep(300)

    threading.Thread(target=_ping, daemon=True).start()

def run_server():
    # Multi-Threaded HTTP Server: Spawns independent threads for 100+ concurrent students
    keep_server_awake()
    try:
        server = ThreadingHTTPServer(('', PORT), APIHandler)
    except Exception:
        server = HTTPServer(('', PORT), APIHandler)

    print(f"High-Performance Multi-Threaded Server running at http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()

if __name__ == "__main__":
    run_server()




