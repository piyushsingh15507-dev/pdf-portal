import urllib.request
import json
import ssl
import urllib.parse

token = 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTgyNTIzNTc0LCJvcmdJZCI6Mjk3NzUyLCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTg4NDc0MjAwMzgiLCJuYW1lIjoiRHJpc2h0aSIsImVtYWlsIjoiZm9ybW1haWw5MTJAZ21haWwuY29tIiwiaXNJbnRlcm5hdGlvbmFsIjowLCJkZWZhdWx0TGFuZ3VhZ2UiOiJFTiIsImNvdW50cnlDb2RlIjoiSU4iLCJjb3VudHJ5SVNPIjoiOTEiLCJ0aW1lem9uZSI6IkdNVCs1OjMwIiwiaXNEaXkiOnRydWUsIm9yZ0NvZGUiOiJ2b2FhZiIsImlzRGl5U3ViYWRtaW4iOjAsImZpbmdlcnByaW50SWQiOiIyM2Q4ZGI4YjhhYThmZDMwNjU3OTQzMGRkOTUxZjk0YiIsImlhdCI6MTc4NTQxNjIzNCwiZXhwIjoxNzg2MDIxMDM0fQ.RTkdTRfNosogL2aPceUWLQk7bi5Aaqf47RsD2JF5TpXV1_6h26QDzyOzfRGRnCnC'
content_id = 'U2FsdGVkX19OMbM3ZcdWpIQMJX813ExA3CmJzmRlTolnkyasL7ZvPrR7JhxnheT7'

ctx = ssl._create_unverified_context()

try:
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
        print(json.dumps(res_json, indent=2))

except Exception as e:
    print("Error:", e)
