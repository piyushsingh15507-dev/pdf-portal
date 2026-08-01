import urllib.request
import ssl
import json
import urllib.parse
import re
import os
import base64
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

    # Get first segment URI
    first_segment_uri = None
    for line in playlist_content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            first_segment_uri = line
            break

    segment_query = resolved_playlist_url.split("?", 1)[1] if "?" in resolved_playlist_url else master_query
    
    # Fetch first segment
    if "?" in first_segment_uri:
        first_segment_url = first_segment_uri if first_segment_uri.startswith("http") else playlist_base + "/" + first_segment_uri
    else:
        first_segment_url = (first_segment_uri if first_segment_uri.startswith("http") else playlist_base + "/" + first_segment_uri) + "?" + segment_query
        
    req_seg = urllib.request.Request(first_segment_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_seg, context=ctx) as res:
        encrypted_segment = res.read()
    
    # Decrypt with o1 parameters to compare
    o1_match = re.search(r'[?&]o1=([A-Za-z0-9+/=]+)', signed_url)
    o1_val = o1_match.group(1)
    raw_o1 = base64.b64decode(o1_val)
    o1_key = raw_o1[:16]
    o1_iv = raw_o1[16:32]

    # Keys to test
    keys_to_test = {
        "o1_key": o1_key,
        "key_bin": bytes.fromhex("426c0311074147700f455d01032d052a"),
        "aes_key_bin": bytes.fromhex("5c514d44071616220e2b2d1c03121e14"),
        "cell_l4_aes_key": bytes.fromhex("101d5611514147760f2b415102420345")
    }

    ivs_to_test = {
        "o1_iv": o1_iv,
        "zero_iv": b'\x00'*16
    }

    for kname, k in keys_to_test.items():
        for ivname, iv in ivs_to_test.items():
            cipher = AES.new(k, AES.MODE_CBC, iv)
            dec = cipher.decrypt(encrypted_segment)
            print(f"Key: {kname:15} | IV: {ivname:8} | Header (Hex): {dec[:16].hex()} | ts? {dec[0] == 0x47}")

except Exception as e:
    print("Error:", e)
