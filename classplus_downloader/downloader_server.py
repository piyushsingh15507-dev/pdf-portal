import os
import sys
import json
import re
import threading
import subprocess
import urllib.request
import urllib.parse
import base64
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None

PORT = 8500
DOWNLOADER_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(DOWNLOADER_DIR)
WORKSPACE_DIR = PARENT_DIR

N_M3U8DL_PATH = os.path.join(PARENT_DIR, "N_m3u8DL-RE.exe")
FFMPEG_PATH = os.path.join(PARENT_DIR, "ffmpeg.exe")

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
extracted_keys_cache = {}
cache_lock = threading.Lock()
SSL_CTX = ssl._create_unverified_context()

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

def decode_o1(url_or_token):
    o1_val = None
    if "o1=" in url_or_token:
        m = re.search(r'[?&]o1=([A-Za-z0-9+/=]+)', url_or_token)
        if m:
            o1_val = m.group(1)
    else:
        cleaned = re.sub(r'[^A-Za-z0-9+/=]', '', url_or_token)
        if len(cleaned) >= 32:
            o1_val = cleaned

    if not o1_val:
        return None, None

    try:
        raw = base64.b64decode(o1_val)
        if len(raw) < 32:
            return None, None

        # Direct decode: first 16 bytes = key, next 16 bytes = iv
        key_bytes = raw[:16]
        iv_hex    = raw[16:32].hex()
        return key_bytes, iv_hex
    except Exception as e:
        print(f"Error decoding o1: {e}")
        return None, None

class DownloaderAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(DOWNLOADER_DIR, "index.html"), "text/html")
        elif path == "/style.css":
            self.serve_file(os.path.join(DOWNLOADER_DIR, "style.css"), "text/css")
        elif path == "/script.js":
            self.serve_file(os.path.join(DOWNLOADER_DIR, "script.js"), "application/javascript")
        elif path == "/api/status":
            self.handle_api_status()
        elif path == "/api/batch-status":
            self.handle_batch_status()
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

    def handle_batch_status(self):
        with batch_lock:
            status = batch_status.copy()
            status["logs"] = "\n".join(batch_status["logs"])
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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

            if o1_input and not o1_input.startswith("U2FsdGVkX19"):
                o1_key, o1_iv = decode_o1(o1_input)
            
            if not o1_key and "o1=" in url:
                o1_key, o1_iv = decode_o1(url)

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
                    match = re.search(r'(U2FsdGVkX19[A-Za-z0-9%+/=]+)', url)
                    if match:
                        content_id = urllib.parse.unquote(match.group(1))

            if not o1_key and content_id and token:
                print(f"Querying Classplus API for contentId: {content_id}")
                api_url = f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId={urllib.parse.quote(content_id)}"
                req = urllib.request.Request(api_url, headers={
                    "x-access-token": token,
                    "region": "IN",
                    "api-version": "26",
                    "Origin": "https://web.classplusapp.com",
                    "Referer": "https://web.classplusapp.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
                            err_msg = res_json.get("error") or res_json.get("message") or "Classplus API authentication failed"
                            raise ValueError(err_msg)
                except Exception as api_err:
                    print(f"API Call failed: {api_err}")
                    self.send_json({"success": False, "error": f"Classplus API Error: {api_err}"}, 400)
                    return

            if o1_key and o1_iv:
                with cache_lock:
                    extracted_keys_cache[resolved_url] = (o1_key, o1_iv)

            if not resolved_url.startswith("http://") and not resolved_url.startswith("https://"):
                self.send_json({"success": False, "error": "Access Token is required when pasting an Encrypted Content ID (U2FsdGVk...). Please enter your Access Token first."}, 400)
                return

            req = urllib.request.Request(resolved_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as response:
                content = response.read().decode('utf-8', errors='ignore')

            streams = []
            if "#EXT-X-STREAM-INF" in content:
                lines = content.split('\n')
                for i in range(len(lines)):
                    line = lines[i].strip()
                    if line.startswith("#EXT-X-STREAM-INF:"):
                        res_match = re.search(r'RESOLUTION=(\d+x\d+)', line)
                        resolution = res_match.group(1) if res_match else "Unknown"
                        
                        bw_match = re.search(r'BANDWIDTH=(\d+)', line)
                        bandwidth = int(bw_match.group(1)) if bw_match else 0
                        
                        stream_url = lines[i+1].strip() if i+1 < len(lines) else ""
                        if stream_url and not stream_url.startswith("#"):
                            full_stream_url = urllib.parse.urljoin(resolved_url, stream_url)
                            streams.append({
                                "resolution": resolution,
                                "bandwidth": bandwidth,
                                "url": full_stream_url
                            })
            else:
                streams.append({
                    "resolution": "Direct Quality",
                    "bandwidth": 0,
                    "url": resolved_url
                })

            output_data = {
                "success": True,
                "streams": streams,
                "has_key": bool(o1_key),
                "key_hex": o1_key.hex() if o1_key else None,
                "iv_hex": o1_iv if o1_iv else None
            }
            self.send_json(output_data)

        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_download(self, data):
        global download_thread, download_status, download_logs
        
        url = data.get("url", "").strip()
        filename = data.get("filename", "Classplus_Video").strip()
        mux_format = data.get("format", "mp4").strip()
        key_hex = data.get("key", "").strip()
        iv_hex = data.get("iv", "").strip()

        if not url:
            self.send_json({"success": False, "message": "Stream URL is required"}, 400)
            return

        with log_lock:
            if download_status["running"]:
                self.send_json({"success": False, "message": "A download is already in progress"}, 400)
                return
            download_logs.clear()
            download_status.update({
                "running": True,
                "progress": 0,
                "speed": "0 Mbps",
                "eta": "--:--",
                "status_text": "Starting...",
                "error": None
            })

        key_bytes = bytes.fromhex(key_hex) if key_hex else None
        if not key_bytes:
            with cache_lock:
                cached = extracted_keys_cache.get(url)
            if not cached:
                o1_k, o1_i = decode_o1(url)
                if o1_k and o1_i:
                    key_bytes = o1_k
                    iv_hex = o1_i
            else:
                key_bytes, iv_hex = cached

        download_thread = threading.Thread(
            target=run_downloader_process,
            args=(url, key_bytes, iv_hex, filename, mux_format)
        )
        download_thread.daemon = True
        download_thread.start()

        self.send_json({"success": True, "message": "Download process initialized."})

def fetch_all_course_videos(token, course_id):
    videos = []
    def traverse_folder(folder_id="0", current_path=""):
        api_url = f"https://api.classplusapp.com/v2/course/content/get?courseId={course_id}&folderId={folder_id}"
        req = urllib.request.Request(api_url, headers={
            "x-access-token": token,
            "region": "IN",
            "api-version": "26",
            "Origin": "https://web.classplusapp.com",
            "Referer": "https://web.classplusapp.com/",
            "User-Agent": "Mozilla/5.0"
        })
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as res:
                res_json = json.loads(res.read().decode('utf-8'))
                if res_json.get("status") == "success":
                    data_obj = res_json.get("data", {})
                    items = data_obj.get("courseContent", data_obj.get("contents", []))
                    for item in items:
                        item_name = item.get("name", "Untitled").strip()
                        item_type = item.get("contentType", item.get("type", 0))
                        item_id = str(item.get("id", ""))
                        content_hash = item.get("contentHashId", "")
                        path_str = f"{current_path}/{item_name}" if current_path else item_name
                        if item_type == 1:
                            traverse_folder(item_id, path_str)
                        elif item_type == 2 or content_hash:
                            content_id = content_hash or item.get("contentId") or item.get("url") or item_id
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
            batch_status["logs"].append(f"[BATCH] Total videos found: {len(videos)}")

        if not videos:
            with batch_lock:
                batch_status["running"] = False
                batch_status["status_text"] = "No videos found."
            return

        output_course_dir = os.path.join(WORKSPACE_DIR, f"Course_{course_id}")
        os.makedirs(output_course_dir, exist_ok=True)

        for idx, vid in enumerate(videos, 1):
            with batch_lock:
                if not batch_status["running"]:
                    batch_status["logs"].append("[BATCH] Batch download cancelled.")
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
                "User-Agent": "Mozilla/5.0"
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
            batch_status["logs"].append("\n[BATCH] 🎉 Batch download completed!")

    except Exception as e:
        with batch_lock:
            batch_status["running"] = False
            batch_status["status_text"] = "Failed"
            batch_status["logs"].append(f"[BATCH] [FATAL ERROR] {e}")

def run_downloader_process(url, key_bytes, iv_hex, filename, mux_format):
    global download_process, download_status, download_logs

    temp_manifest_path = os.path.join(WORKSPACE_DIR, "_temp_manifest.m3u8")
    temp_key_path = os.path.join(WORKSPACE_DIR, "_temp_key.bin")
    output_file = os.path.join(WORKSPACE_DIR, f"{filename}.{mux_format}")

    try:
        with log_lock:
            download_logs.append(f"[SYSTEM] Starting download for: {filename}.{mux_format}")

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as response:
            playlist_content = response.read().decode('utf-8', errors='ignore')
            final_url = response.url

        lines = playlist_content.split('\n')
        key_server_uri = None
        for line in lines:
            if line.strip().startswith("#EXT-X-KEY:"):
                m = re.search(r'URI="([^"]+)"', line)
                if m:
                    key_server_uri = m.group(1)
                    break

        if "#EXT-X-STREAM-INF" in playlist_content:
            best_bw, best_uri = -1, None
            plines = playlist_content.split('\n')
            for i, pline in enumerate(plines):
                if pline.strip().startswith("#EXT-X-STREAM-INF"):
                    bw_m = re.search(r'BANDWIDTH=(\d+)', pline)
                    bw = int(bw_m.group(1)) if bw_m else 0
                    if bw > best_bw and i+1 < len(plines):
                        next_line = plines[i+1].strip()
                        if next_line and not next_line.startswith("#"):
                            best_bw = bw
                            best_uri = next_line
            if best_uri:
                quality_url = best_uri if best_uri.startswith("http") else urllib.parse.urljoin(final_url, best_uri)
                with log_lock:
                    download_logs.append(f"[SYSTEM] Master playlist detected. Selecting best quality: {quality_url[:80]}...")
                req2 = urllib.request.Request(quality_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req2, context=SSL_CTX, timeout=15) as r2:
                    playlist_content = r2.read().decode('utf-8', errors='ignore')
                    url = r2.url
                    final_url = url

        lines = playlist_content.split('\n')
        if not key_server_uri:
            for line in lines:
                if line.strip().startswith("#EXT-X-KEY:"):
                    m = re.search(r'URI="([^"]+)"', line)
                    if m:
                        key_server_uri = m.group(1)
                        break

        if key_server_uri:
            with log_lock:
                download_logs.append(f"[SYSTEM] EXT-X-KEY found: {key_server_uri[:80]}")
        else:
            with log_lock:
                download_logs.append("[SYSTEM] No EXT-X-KEY in playlist — plain HLS or already patched")

        real_key_bytes = None
        query_str = url.split("?", 1)[1] if "?" in url else ""

        if key_server_uri and key_bytes:
            if not key_server_uri.startswith("http"):
                key_server_uri = urllib.parse.urljoin(url, key_server_uri)

            if "?" not in key_server_uri and query_str:
                orig_params = urllib.parse.parse_qs(query_str)
                cdn_params = {}
                for param in ["key", "Expires", "Signature", "URLPrefix", "_GO", "userIds", "hdnts", "hmac"]:
                    if param in orig_params:
                        cdn_params[param] = orig_params[param][0]
                if cdn_params:
                    key_server_uri = f"{key_server_uri}?{urllib.parse.urlencode(cdn_params)}"

            with log_lock:
                download_logs.append(f"[SYSTEM] Key server URI: {key_server_uri[:90]}...")
                download_logs.append("[SYSTEM] Fetching key blob...")

            try:
                req_key = urllib.request.Request(key_server_uri, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req_key, context=SSL_CTX, timeout=15) as r_key:
                    encrypted_blob = r_key.read()

                if AES:
                    iv_bytes = bytes.fromhex(iv_hex) if iv_hex else b'\x00' * 16
                    blob_padded = encrypted_blob
                    if len(blob_padded) % 16 != 0:
                        blob_padded += b'\x00' * (16 - len(blob_padded) % 16)
                    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
                    decrypted_blob = cipher.decrypt(blob_padded)
                    real_key_bytes = decrypted_blob[:16]
                    with log_lock:
                        download_logs.append(f"[SYSTEM] Decrypted segment key: {real_key_bytes.hex()}")
            except Exception as k_err:
                with log_lock:
                    download_logs.append(f"[SYSTEM] [WARNING] Key server fetch failed: {k_err}")

        if not real_key_bytes and key_bytes:
            real_key_bytes = key_bytes

        if real_key_bytes:
            with open(temp_key_path, "wb") as f:
                f.write(real_key_bytes)
            
            abs_key_path = os.path.abspath(temp_key_path)
            key_file_uri = "file:///" + urllib.parse.quote(abs_key_path.replace("\\", "/"), safe="/:")
            
            key_tag = f'#EXT-X-KEY:METHOD=AES-128,URI="{key_file_uri}"'
            if iv_hex:
                key_tag += f',IV=0x{iv_hex}'

            new_lines = []
            has_key_tag = False
            for line in lines:
                if line.strip().startswith("#EXT-X-KEY:"):
                    new_lines.append(key_tag)
                    has_key_tag = True
                elif line.strip() and not line.strip().startswith("#"):
                    abs_seg_url = urllib.parse.urljoin(url, line.strip())
                    new_lines.append(abs_seg_url)
                else:
                    new_lines.append(line)

            if not has_key_tag:
                manifest_lines = []
                inserted = False
                for line in new_lines:
                    manifest_lines.append(line)
                    if line.strip().startswith("#EXTINF:") and not inserted:
                        manifest_lines.insert(len(manifest_lines)-1, key_tag)
                        inserted = True
                new_lines = manifest_lines

            with open(temp_manifest_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
        else:
            new_lines = []
            for line in lines:
                if line.strip() and not line.strip().startswith("#"):
                    new_lines.append(urllib.parse.urljoin(url, line.strip()))
                else:
                    new_lines.append(line)
            with open(temp_manifest_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))

        # Run FFmpeg
        cmd = [
            FFMPEG_PATH, "-y",
            "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "-headers", "Origin: https://web.classplusapp.com\r\nReferer: https://web.classplusapp.com/\r\n",
            "-allowed_extensions", "ALL",
            "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
            "-i", temp_manifest_path,
            "-c", "copy",
            output_file
        ]

        with log_lock:
            download_logs.append(f"[CMD] Launching FFmpeg downloader...")

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=WORKSPACE_DIR, bufsize=1)
        download_process = proc

        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
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

        proc_exit = proc.wait()
        with log_lock:
            download_status["running"] = False
            if proc_exit == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                download_status["progress"] = 100
                download_status["status_text"] = "Completed"
                download_logs.append(f"[SYSTEM] Success! Video saved: '{filename}.{mux_format}'")
            else:
                download_status["status_text"] = "Failed"
                download_logs.append("[SYSTEM] [ERROR] Downloader failed.")

    except Exception as e:
        with log_lock:
            download_status["running"] = False
            download_status["status_text"] = "Failed"
            download_logs.append(f"[SYSTEM] [FATAL ERROR] {e}")

def run_server():
    server = HTTPServer(('', PORT), DownloaderAPIHandler)
    print(f"Dedicated Classplus Downloader running at http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()

if __name__ == "__main__":
    run_server()
