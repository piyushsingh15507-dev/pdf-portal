import urllib.request
import ssl
import json
import urllib.parse
import re

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

    print("--- Playlist Content ---")
    print(playlist_content[:1500])
    print("...")
    print(playlist_content[-500:])

except Exception as e:
    print("Error:", e)
