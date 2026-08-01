import urllib.request
import ssl
import json
import urllib.parse
import base64
import re
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
    # 1. Fetch fresh signed URL
    print("--- Fetching Fresh Signed URL ---")
    api_url = f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId={urllib.parse.quote(content_id)}"
    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        res_json = json.loads(res.read().decode('utf-8'))
        signed_url = res_json.get("url")
        print("Success! Signed URL:")
        print(signed_url[:120] + "...")

    # 2. Decode o1
    o1_match = re.search(r'[?&]o1=([A-Za-z0-9+/=]+)', signed_url)
    o1_val = o1_match.group(1)
    raw_o1 = base64.b64decode(o1_val)
    o1_key = raw_o1[:16]
    o1_iv = raw_o1[16:32]
    
    print("\no1 Key (Hex):", o1_key.hex())
    print("o1 IV (Hex) :", o1_iv.hex())

    # Get signed query parameters from master URL to preserve signatures
    master_parsed = urllib.parse.urlparse(signed_url)
    master_query = master_parsed.query
    
    # 3. Fetch master manifest
    req_master = urllib.request.Request(signed_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_master, context=ctx) as res:
        master_content = res.read().decode('utf-8')
        resolved_master_url = res.url
        master_base = resolved_master_url.rsplit("/", 1)[0]
    
    # 4. Get first quality playlist URL
    sub_playlist_uri = None
    for line in master_content.splitlines():
        if line.strip() and not line.startswith("#"):
            sub_playlist_uri = line.strip()
            break
            
    connector = "&" if "?" in sub_playlist_uri else "?"
    sub_playlist_url = (sub_playlist_uri if sub_playlist_uri.startswith("http") else master_base + "/" + sub_playlist_uri) + connector + master_query

    # 5. Fetch playlist content
    req_playlist = urllib.request.Request(sub_playlist_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_playlist, context=ctx) as res:
        playlist_content = res.read().decode('utf-8')
        resolved_playlist_url = res.url
        playlist_base = resolved_playlist_url.rsplit("/", 1)[0]

    # Print first 20 lines of playlist
    print("\n--- Playlist Manifest (First 20 lines) ---")
    lines = playlist_content.splitlines()
    for i in range(min(20, len(lines))):
        print(f"{i+1:02d}: {lines[i]}")

    # 6. Extract first segment URL and key server URI
    key_server_uri = None
    first_segment_uri = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXT-X-KEY:"):
            m = re.search(r'URI="([^"]+)"', line)
            if m: key_server_uri = m.group(1)
        elif line and not line.startswith("#"):
            first_segment_uri = line
            break

    segment_query = resolved_playlist_url.split("?", 1)[1] if "?" in resolved_playlist_url else master_query
    
    # 7. Fetch first segment
    if "?" in first_segment_uri:
        first_segment_url = first_segment_uri if first_segment_uri.startswith("http") else playlist_base + "/" + first_segment_uri
    else:
        first_segment_url = (first_segment_uri if first_segment_uri.startswith("http") else playlist_base + "/" + first_segment_uri) + "?" + segment_query
        
    print("\nFetching first segment...")
    req_seg = urllib.request.Request(first_segment_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_seg, context=ctx) as res:
        encrypted_segment = res.read()
    
    print("Segment Size:", len(encrypted_segment), "bytes")

    # Try direct decryption with o1_key and o1_iv
    cipher = AES.new(o1_key, AES.MODE_CBC, o1_iv)
    decrypted = cipher.decrypt(encrypted_segment)
    print("Decrypted segment header (Hex):", decrypted[:16].hex())
    if decrypted[0] == 0x47:
        print("[✓] Decrypted successfully using o1 Key + o1 IV directly!")
    else:
        print("[X] Failed to decrypt directly.")

    # 8. Check if there is an encrypted key blob from key server
    if key_server_uri:
        if not key_server_uri.startswith("http"):
            key_server_uri = urllib.parse.urljoin(sub_playlist_url, key_server_uri)
        if "?" not in key_server_uri:
            key_server_uri = key_server_uri + "?" + segment_query
            
        print("\nFetching key blob from server:", key_server_uri[:120] + "...")
        req_key = urllib.request.Request(key_server_uri, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_key, context=ctx) as res:
            encrypted_blob = res.read()
        print("Encrypted key blob (Hex):", encrypted_blob.hex())
        
        # Decrypt blob using o1 Key + o1 IV
        cipher_k = AES.new(o1_key, AES.MODE_CBC, o1_iv)
        decrypted_blob = cipher_k.decrypt(encrypted_blob)
        print("Decrypted blob (Hex):", decrypted_blob.hex())
        
        # Real decryption key is first 16 bytes
        real_key = decrypted_blob[:16]
        print("Real Decrypted Key (Hex):", real_key.hex())

        # Test real key with zero IV and o1_iv
        for name, iv in [("zero_iv", b'\x00'*16), ("o1_iv", o1_iv)]:
            cipher_test = AES.new(real_key, AES.MODE_CBC, iv)
            dec_test = cipher_test.decrypt(encrypted_segment)
            print(f"Decrypted header with real key + {name} (Hex):", dec_test[:16].hex())
            if dec_test[0] == 0x47:
                print(f"[✓] SUCCESS! Decrypted correctly with real key + {name}!")

except Exception as e:
    print("Error:", e)
