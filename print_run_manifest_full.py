import os

path = r'C:\Users\HP\Downloads\hls live classplus\tmp_m3u8_run\run_240p.m3u8'
if os.path.exists(path):
    print("--- run_240p.m3u8 full ---")
    lines = open(path, encoding='utf-8').read().splitlines()
    for idx, line in enumerate(lines):
        print(f"{idx+1:03d}: {line}")
else:
    print("File not found")
