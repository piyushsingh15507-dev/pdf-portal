import urllib.request
import ssl
import json
import urllib.parse
import base64
import re
from Crypto.Cipher import AES

token = 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTgyNTIzNTc0LCJvcmdJZCI6Mjk3NzUyLCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTg4NDc0MjAwMzgiLCJuYW1lIjoiRHJpc2h0aSIsImVtYWlsIjoiZm9ybW1haWw5MTJAZ21haWwuY29tIiwiaXNJbnRlcm5hdGlvbmFsIjowLCJkZWZhdWx0TGFuZ3VhZ2UiOiJFTiIsImNvdW50cnlDb2RlIjoiSU4iLCJjb3VudHJ5SVNPIjoiOTEiLCJ0aW1lem9uZSI6IkdNVCs1OjMwIiwiaXNEaXkiOnRydWUsIm9yZ0NvZGUiOiJ2b2FhZiIsImlzRGl5U3ViYWRtaW4iOjAsImZpbmdlcnByaW50SWQiOiIxODMxMDBmYWQ1YTViYjdhYmUzMjJhMDdmMjA2MWQ5MyIsImlhdCI6MTc4NTUxOTgxMiwiZXhwIjoxNzg2MTI0NjEyfQ.a-a2lyjwEdns258v48b8esiCtgEGee6pmLol0OqZNxRpW-8iPGiNcD9HI-sgQCt6'
content_id = 'U2FsdGVkX1+79LvNmB8nP8xBZHAKXRZzbQX6YLEO5CpGz7KAbkqLFpjywuotTeE2'
signed_url = 'https://media-cdn.classplusapp.com/297752/cc/5543157cad004094bc97c38cd67e683e-66_encn/master.m3u8?key=182523574&hdnts=URLPrefix=aHR0cHM6Ly9tZWRpYS1jZG4uY2xhc3NwbHVzYXBwLmNvbS8yOTc3NTIvY2MvNTU0MzE1N2NhZDAwNDA5NGJjOTdjMzhjZDY3ZTY4M2UtNjZfZW5jbg~Expires=1785531668~hmac=4bebdb3bb700b2c569a0fac0e587e8a3883c38ea7250d04a0a252ae7ddfc4c3a&userIds=182523574&o1=LW1RR1EqRnEPFUAdTBAGQXp2WCtCAQFdHUB6IzIWRwbc1mYBcjbT0BNQTlxTRQpyWkJBHFYsUhVEIVwUQQFXQh1Be3FDRS1Q'

ctx = ssl._create_unverified_context()

try:
    # 1. Decode o1
    o1_match = re.search(r'[?&]o1=([A-Za-z0-9+/=]+)', signed_url)
    o1_val = o1_match.group(1)
    raw_o1 = base64.b64decode(o1_val)
    o1_key = raw_o1[:16]
    o1_iv = raw_o1[16:32]
    
    print("o1 Key (Hex):", o1_key.hex())
    print("o1 IV (Hex) :", o1_iv.hex())

    # 2. Fetch master manifest
    headers = {
        "x-access-token": token,
        "Origin": "https://app.sciastra.com",
        "Referer": "https://app.sciastra.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    req_master = urllib.request.Request(signed_url, headers=headers)
    with urllib.request.urlopen(req_master, context=ctx) as res:
        master_content = res.read().decode('utf-8')
        resolved_master_url = res.url
        master_base = resolved_master_url.rsplit("/", 1)[0]
    
    print("Master content length:", len(master_content))
    
    # 3. Get first quality playlist URL
    sub_playlist_uri = None
    for line in master_content.splitlines():
        if line.strip() and not line.startswith("#"):
            sub_playlist_uri = line.strip()
            break
            
    sub_playlist_url = sub_playlist_uri if sub_playlist_uri.startswith("http") else master_base + "/" + sub_playlist_uri
    print("Playlist URL:", sub_playlist_url[:120] + "...")

    # 4. Fetch playlist content
    req_playlist = urllib.request.Request(sub_playlist_url, headers=headers)
    with urllib.request.urlopen(req_playlist, context=ctx) as res:
        playlist_content = res.read().decode('utf-8')
        resolved_playlist_url = res.url
        playlist_base = resolved_playlist_url.rsplit("/", 1)[0]

    # Print first 20 lines of playlist
    print("\n--- Playlist Manifest (First 20 lines) ---")
    lines = playlist_content.splitlines()
    for i in range(min(20, len(lines))):
        print(f"{i+1:02d}: {lines[i]}")

    # 5. Extract first segment URL and key server URI
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

    # 6. Fetch first segment
    first_segment_url = first_segment_uri if first_segment_uri.startswith("http") else playlist_base + "/" + first_segment_uri
    print("\nFetching first segment:", first_segment_url[:120] + "...")
    req_seg = urllib.request.Request(first_segment_url, headers=headers)
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

    # 7. Check if there is an encrypted key blob from key server
    if key_server_uri:
        if not key_server_uri.startswith("http"):
            key_server_uri = urllib.parse.urljoin(sub_playlist_url, key_server_uri)
        print("\nFetching key blob from server:", key_server_uri[:120] + "...")
        req_key = urllib.request.Request(key_server_uri, headers=headers)
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
