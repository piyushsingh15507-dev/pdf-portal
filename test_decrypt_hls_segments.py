import urllib.request
import ssl
import json
import urllib.parse
import base64
import re
import os
import subprocess
from Crypto.Cipher import AES

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
    api_url = f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId={urllib.parse.quote(content_id)}"
    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        res_json = json.loads(res.read().decode('utf-8'))
        signed_url = res_json.get("url")

    # Decode o1
    o1_match = re.search(r'[?&]o1=([A-Za-z0-9+/=]+)', signed_url)
    o1_val = o1_match.group(1)
    raw_o1 = base64.b64decode(o1_val)
    o1_key = raw_o1[:16]
    o1_iv = raw_o1[16:32]

    print("o1 Key:", o1_key.hex())
    print("o1 IV :", o1_iv.hex())

    # Get signed query parameters from master URL to preserve signatures
    master_parsed = urllib.parse.urlparse(signed_url)
    master_query = master_parsed.query

    # Fetch master manifest
    req_master = urllib.request.Request(signed_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_master, context=ctx) as res:
        master_content = res.read().decode('utf-8')
        resolved_master_url = res.url
        master_base = resolved_master_url.rsplit("/", 1)[0]
    
    # Get first quality playlist URL
    sub_playlist_uri = None
    for line in master_content.splitlines():
        if line.strip() and not line.startswith("#"):
            sub_playlist_uri = line.strip()
            break
            
    connector = "&" if "?" in sub_playlist_uri else "?"
    sub_playlist_url = (sub_playlist_uri if sub_playlist_uri.startswith("http") else master_base + "/" + sub_playlist_uri) + connector + master_query

    # Fetch playlist content
    req_playlist = urllib.request.Request(sub_playlist_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_playlist, context=ctx) as res:
        playlist_content = res.read().decode('utf-8')
        resolved_playlist_url = res.url
        playlist_base = resolved_playlist_url.rsplit("/", 1)[0]

    # Get first two segment URIs
    segment_uris = []
    for line in playlist_content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            segment_uris.append(line)
            if len(segment_uris) == 2:
                break

    segment_query = resolved_playlist_url.split("?", 1)[1] if "?" in resolved_playlist_url else master_query
    
    ffmpeg_path = r'c:\Users\HP\Downloads\hls live classplus\ffmpeg.exe'

    for idx, uri in enumerate(segment_uris):
        if "?" in uri:
            url = uri if uri.startswith("http") else playlist_base + "/" + uri
        else:
            url = (uri if uri.startswith("http") else playlist_base + "/" + uri) + "?" + segment_query
            
        print(f"\n--- Downloading Segment {idx} ---")
        req_seg = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_seg, context=ctx) as res:
            enc_data = res.read()
            
        # Decrypt segment using o1_key and o1_iv (HLS AES-128 standard uses segment number or key IV)
        # We will try both o1_iv and sequence IV (since segment index is idx)
        for iv_name, test_iv in [("o1_iv", o1_iv), ("seq_iv", idx.to_bytes(16, "big"))]:
            cipher = AES.new(o1_key, AES.MODE_CBC, test_iv)
            dec_data = cipher.decrypt(enc_data)
            
            # Write to a temp file to run ffmpeg validation
            tmp_filename = f"temp_seg_{idx}_{iv_name}.ts"
            with open(tmp_filename, "wb") as f:
                f.write(dec_data)
                
            res_ff = subprocess.run([ffmpeg_path, '-i', tmp_filename], capture_output=True, text=True)
            print(f"IV: {iv_name} -> ffmpeg result:")
            if "mpegts" in res_ff.stderr:
                print(f"  [✓] SUCCESS! MPEG-TS stream detected!")
            else:
                print(f"  [X] Failed. Header start: {dec_data[:16].hex()}")
            
            # Clean up
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)

except Exception as e:
    print("Error:", e)
