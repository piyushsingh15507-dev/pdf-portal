import urllib.request
import ssl
import json
import urllib.parse
import re

token = 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTgyNTIzNTc0LCJvcmdJZCI6Mjk3NzUyLCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTg4NDc0MjAwMzgiLCJuYW1lIjoiRHJpc2h0aSIsImVtYWlsIjoiZm9ybW1haWw5MTJAZ21haWwuY29tIiwiaXNJbnRlcm5hdGlvbmFsIjowLCJkZWZhdWx0TGFuZ3VhZ2UiOiJFTiIsImNvdW50cnlDb2RlIjoiSU4iLCJjb3VudHJ5SVNPIjoiOTEiLCJ0aW1lem9uZSI6IkdNVCs1OjMwIiwiaXNEaXkiOnRydWUsIm9yZ0NvZGUiOiJ2b2FhZiIsImlzRGl5U3ViYWRtaW4iOjAsImZpbmdlcnByaW50SWQiOiIxODMxMDBmYWQ1YTViYjdhYmUzMjJhMDdmMjA2MWQ5MyIsImlhdCI6MTc4NTUxOTgxMiwiZXhwIjoxNzg2MTI0NjEyfQ.a-a2lyjwEdns258v48b8esiCtgEGee6pmLol0OqZNxRpW-8iPGiNcD9HI-sgQCt6'
signed_url = 'https://media-cdn.classplusapp.com/297752/cc/5543157cad004094bc97c38cd67e683e-66_encn/master.m3u8?key=182523574&hdnts=URLPrefix=aHR0cHM6Ly9tZWRpYS1jZG4uY2xhc3NwbHVzYXBwLmNvbS8yOTc3NTIvY2MvNTU0MzE1N2NhZDAwNDA5NGJjOTdjMzhjZDY3ZTY4M2UtNjZfZW5jbg~Expires=1785531668~hmac=4bebdb3bb700b2c569a0fac0e587e8a3883c38ea7250d04a0a252ae7ddfc4c3a&userIds=182523574&o1=LW1RR1EqRnEPFUAdTBAGQXp2WCtCAQFdHUB6IzIWRwbc1mYBcjbT0BNQTlxTRQpyWkJBHFYsUhVEIVwUQQFXQh1Be3FDRS1Q'

ctx = ssl._create_unverified_context()
headers = {
    "x-access-token": token,
    "Origin": "https://app.sciastra.com",
    "Referer": "https://app.sciastra.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Step 1: Master
try:
    print("--- Fetching Master Manifest ---")
    print("URL:", signed_url)
    req = urllib.request.Request(signed_url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        content = res.read().decode('utf-8')
        print("Success! Master manifest size:", len(content))
        print("URL after redirects:", res.url)
        print("Response headers:")
        for k, v in res.info().items():
            print(f"  {k}: {v}")
except Exception as e:
    print("Master Fetch Failed:", e)
