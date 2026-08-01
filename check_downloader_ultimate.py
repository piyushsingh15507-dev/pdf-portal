import sys

path = r'C:\Users\HP\Downloads\sciastra_standalone\sciastra_downloader_ultimate.py'
lines = open(path, encoding='utf-8').readlines()

for idx in range(min(250, len(lines))):
    line = lines[idx]
    sys.stdout.buffer.write(f"{idx+1:03d}: ".encode('utf-8') + line.encode('utf-8'))
