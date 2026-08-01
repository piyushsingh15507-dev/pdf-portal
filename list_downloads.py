import os
import sys

folder = r'C:\Users\HP\Downloads'
files = os.listdir(folder)

for f in sorted(files):
    try:
        sys.stdout.buffer.write((f + "\n").encode('utf-8'))
    except Exception:
        pass
