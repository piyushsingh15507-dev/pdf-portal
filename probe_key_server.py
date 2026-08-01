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
    # 1. Get fresh signed URL
    api_url = f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?contentId={urllib.parse.quote(content_id)}"
    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        res_json = json.loads(res.read().decode('utf-8'))
        signed_url = res_json.get("url")

    # Get signature parameters
    parsed = urllib.parse.urlparse(signed_url)
    sig_query = parsed.query

    # Base URLs
    cdn_base_parent = signed_url.split("/master.m3u8")[0]
    cdn_base_quality = cdn_base_parent + "/720"

    print("Parent Base :", cdn_base_parent)
    print("Quality Base:", cdn_base_quality)
    print()

    # Paths to probe
    probe_targets = [
        # Parent level
        f"{cdn_base_parent}/key.bin",
        f"{cdn_base_parent}/_key.bin",
        f"{cdn_base_parent}/_aes_key.bin",
        f"{cdn_base_parent}/key",
        # Quality level
        f"{cdn_base_quality}/key.bin",
        f"{cdn_base_quality}/_key.bin",
        f"{cdn_base_quality}/_aes_key.bin",
        f"{cdn_base_quality}/key",
    ]

    for target in probe_targets:
        url_with_sig = target + "?" + sig_query
        print(f"Probing: {target} ... ", end="")
        try:
            req_probe = urllib.request.Request(url_with_sig, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_probe, context=ctx, timeout=5) as res:
                data = res.read()
                print(f"SUCCESS! Status 200, Size: {len(data)} bytes, Hex: {data.hex()[:40]}")
        except urllib.error.HTTPError as e:
            print(f"FAILED (HTTP {e.code})")
        except Exception as e:
            print(f"FAILED ({e})")

except Exception as e:
    print("Error:", e)
