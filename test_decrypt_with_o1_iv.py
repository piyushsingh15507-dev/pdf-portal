import urllib.request
import ssl
import json
import urllib.parse
from Crypto.Cipher import AES

token = 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTgyNTIzNTc0LCJvcmdJZCI6Mjk3NzUyLCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTg4NDc0MjAwMzgiLCJuYW1lIjoiRHJpc2h0aSIsImVtYWlsIjoiZm9ybW1haWw5MTJAZ21haWwuY29tIiwiaXNJbnRlcm5hdGlvbmFsIjowLCJkZWZhdWx0TGFuZ3VhZ2UiOiJFTiIsImNvdW50cnlDb2RlIjoiSU4iLCJjb3VudHJ5SVNPIjoiOTEiLCJ0aW1lem9uZSI6IkdNVCs1OjMwIiwiaXNEaXkiOnRydWUsIm9yZ0NvZGUiOiJ2b2FhZiIsImlzRGl5U3ViYWRtaW4iOjAsImZpbmdlcnByaW50SWQiOiIyM2Q4ZGI4YjhhYThmZDMwNjU3OTQzMGRkOTUxZjk0YiIsImlhdCI6MTc4NTQxNjIzNCwiZXhwIjoxNzg2MDIxMDM0fQ.RTkdTRfNosogL2aPceUWLQk7bi5Aaqf47RsD2JF5TpXV1_6h26QDzyOzfRGRnCnC'
content_id = 'U2FsdGVkX19OMbM3ZcdWpIQMJX813ExA3CmJzmRlTolnkyasL7ZvPrR7JhxnheT7'
ctx = ssl._create_unverified_context()

try:
    # 1. Fetch signed URL
    api_url = f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId={urllib.parse.quote(content_id)}"
    req = urllib.request.Request(api_url, headers={
        "x-access-token": token,
        "region": "IN",
        "api-version": "26",
        "Origin": "https://web.classplusapp.com",
        "Referer": "https://web.classplusapp.com/",
        "User-Agent": "Mozilla/5.0"
    })
    
    with urllib.request.urlopen(req, context=ctx) as res:
        res_json = json.loads(res.read().decode('utf-8'))
        signed_url = res_json.get("url")

    # 2. Decode o1 Key and IV
    import base64
    import re
    m = re.search(r'[?&]o1=([A-Za-z0-9+/=]+)', signed_url)
    raw = base64.b64decode(m.group(1))
    o1_key = raw[:16]
    o1_iv = raw[16:32]

    # 3. Resolve quality sub-playlist URL
    req_master = urllib.request.Request(signed_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_master, context=ctx) as res:
        master_content = res.read().decode('utf-8', errors='ignore')
        master_base = res.url.rsplit("/", 1)[0]

    sub_playlist_uri = None
    for line in master_content.splitlines():
        if line.strip() and not line.startswith("#"):
            sub_playlist_uri = line.strip()
            break
    sub_playlist_url = sub_playlist_uri if sub_playlist_uri.startswith("http") else master_base + "/" + sub_playlist_uri

    # 4. Fetch sub-playlist manifest contents
    req_playlist = urllib.request.Request(sub_playlist_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_playlist, context=ctx) as res:
        playlist_content = res.read().decode('utf-8', errors='ignore')
        playlist_base = res.url.rsplit("/", 1)[0]
    
    first_segment_uri = None
    for line in playlist_content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            first_segment_uri = line
            break

    # 5. Fetch first segment data
    first_segment_url = first_segment_uri if first_segment_uri.startswith("http") else playlist_base + "/" + first_segment_uri
    req_seg = urllib.request.Request(first_segment_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_seg, context=ctx) as r_seg:
        encrypted_segment = r_seg.read()

    print("o1 Key (Hex):", o1_key.hex())
    print("o1 IV (Hex) :", o1_iv.hex())
    print("Segment Size:", len(encrypted_segment), "bytes")

    # Try decrypting with o1_iv!
    cipher = AES.new(o1_key, AES.MODE_CBC, o1_iv)
    dec = cipher.decrypt(encrypted_segment)
    print("\nFirst 16 decrypted bytes:")
    print("Hex   :", dec[:16].hex())
    print("Ascii :", dec[:16])
    
    if dec[0] == 0x47:
        print("\n[✓] SUCCESS! Decrypted successfully using o1 Key + o1 IV!")
    else:
        print("\n[X] FAILED! First byte is not 0x47 (MPEG-TS Sync).")

except Exception as e:
    print("Error:", e)
