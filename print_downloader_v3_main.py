import sys

path = r'C:\Users\HP\Downloads\sciastra_downloader_v3.py'
lines = open(path, encoding='utf-8').readlines()

# Print lines 361 to 450
for idx in range(360, min(450, len(lines))):
    line = lines[idx]
    sys.stdout.buffer.write(f"{idx+1:03d}: ".encode('utf-8') + line.encode('utf-8'))
