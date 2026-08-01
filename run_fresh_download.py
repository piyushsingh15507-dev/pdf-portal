import urllib.request
import ssl
import json
import urllib.parse
import re
import os
import subprocess
from pathlib import Path

token = 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTgyNTIzNTc0LCJvcmdJZCI6Mjk3NzUyLCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTg4NDc0MjAwMzgiLCJuYW1lIjoiRHJpc2h0aSIsImVtYWlsIjoiZm9ybW1haWw5MTJAZ21haWwuY29tIiwiaXNJbnRlcm5hdGlvbmFsIjowLCJkZWZhdWx0TGFuZ3VhZ2UiOiJFTiIsImNvdW50cnlDb2RlIjoiSU4iLCJjb3VudHJ5SVNPIjoiOTEiLCJ0aW1lem9uZSI6IkdNVCs1OjMwIiwiaXNEaXkiOnRydWUsIm9yZ0NvZGUiOiJ2b2FhZiIsImlzRGl5U3ViYWRtaW4iOjAsImZpbmdlcnByaW50SWQiOiIxODMxMDBmYWQ1YTViYjdhYmUzMjJhMDdmMjA2MWQ5MyIsImlhdCI6MTc4NTUxOTgxMiwiZXhwIjoxNzg2MTI0NjEyfQ.a-a2lyjwEdns258v48b8esiCtgEGee6pmLol0OqZNxRpW-8iPGiNcD9HI-sgQCt6'
content_id = 'U2FsdGVkX1+79LvNmB8nP8xBZHAKXRZzbQX6YLEO5CpGz7KAbkqLFpjywuotTeE2'

ctx = ssl._create_unverified_context()
headers = {
    "x-access-token": token,
    "region": "IN",
    "api-version": "26",
    "Origin": "https://app.sciastra.com",
    "Referer": "https://app.sciastra.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    print("[1] Fetching fresh signed URL...")
    api_url = f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId={urllib.parse.quote(content_id)}"
    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        res_json = json.loads(res.read().decode('utf-8'))
        signed_url = res_json.get("url")

    # Get signed query parameters from master URL to preserve signatures
    master_parsed = urllib.parse.urlparse(signed_url)
    master_query = master_parsed.query

    # Fetch master manifest
    req_master = urllib.request.Request(signed_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_master, context=ctx) as res:
        master_content = res.read().decode('utf-8')
        resolved_master_url = res.url
        master_base = resolved_master_url.rsplit("/", 1)[0]
    
    # Get 240p quality playlist URL (to download quickly for testing)
    sub_playlist_uri = None
    for line in master_content.splitlines():
        if line.strip() and not line.startswith("#") and "240" in line:
            sub_playlist_uri = line.strip()
            break
            
    if not sub_playlist_uri:
        # Fallback to first resolution
        for line in master_content.splitlines():
            if line.strip() and not line.startswith("#"):
                sub_playlist_uri = line.strip()
                break

    connector = "&" if "?" in sub_playlist_uri else "?"
    sub_playlist_url = (sub_playlist_uri if sub_playlist_uri.startswith("http") else master_base + "/" + sub_playlist_uri) + connector + master_query

    print("[2] Fetching quality playlist...")
    req_playlist = urllib.request.Request(sub_playlist_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_playlist, context=ctx) as res:
        playlist_content = res.read().decode('utf-8')
        resolved_playlist_url = res.url
        playlist_base = resolved_playlist_url.rsplit("/", 1)[0]

    # Set Key and IV
    real_key_hex = "fe2184d0b17163c4ad4336f32e6504a7"
    iv_hex = "7a76582b4201015d1d407a2332164706"

    tmp_dir = Path("./tmp_m3u8_run")
    tmp_dir.mkdir(exist_ok=True)
    
    key_file = tmp_dir / "key.bin"
    key_file.write_bytes(bytes.fromhex(real_key_hex))
    
    patched_lines = []
    # Inject EXT-X-KEY at the beginning
    patched_lines.append("#EXTM3U")
    patched_lines.append("#EXT-X-VERSION:3")
    patched_lines.append(f'#EXT-X-KEY:METHOD=AES-128,URI="key.bin",IV=0x{iv_hex}')

    query_str = resolved_playlist_url.split("?", 1)[1] if "?" in resolved_playlist_url else master_query

    for line in playlist_content.splitlines():
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U") or line_str.startswith("#EXT-X-VERSION") or line_str.startswith("#EXT-X-KEY"):
            continue
        if not line_str.startswith("#"):
            if line_str.startswith("http"):
                segment_url = line_str
            else:
                sep = "&" if "?" in line_str else "?"
                segment_url = f"{playlist_base}/{line_str}{sep}{query_str}" if query_str and "?" not in line_str else f"{playlist_base}/{line_str}"
            patched_lines.append(segment_url)
        else:
            patched_lines.append(line_str)

    local_m3u8 = tmp_dir / "run_240p.m3u8"
    local_m3u8.write_text("\n".join(patched_lines), encoding="utf-8")
    print(f"[3] Created patched local playlist")

    output_path = Path("Test_Classplus_240p_Decrypted.mp4").resolve()
    if output_path.exists():
        output_path.unlink()

    print(f"[4] Downloading & decrypting with ffmpeg...")
    cmd = [
        "ffmpeg",
        "-y",
        "-allowed_extensions", "ALL",
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
        "-i", "run_240p.m3u8",
        "-c", "copy",
        str(output_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_dir.resolve()))
    if output_path.exists() and output_path.stat().st_size > 100000:
        print(f"SUCCESS: Decrypted video size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    else:
        print(f"FFmpeg failed: {res.stderr[-500:]}")

except Exception as e:
    print("Error:", e)
