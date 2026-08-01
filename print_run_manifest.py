import os

path = r'C:\Users\HP\Downloads\hls live classplus\tmp_m3u8_run\run_240p.m3u8'
if os.path.exists(path):
    print("--- run_240p.m3u8 ---")
    lines = open(path, encoding='utf-8').read().splitlines()
    for idx in range(min(20, len(lines))):
        print(f"{idx+1:02d}: {lines[idx]}")
else:
    print("File not found")
