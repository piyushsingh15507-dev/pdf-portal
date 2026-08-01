import os
import subprocess

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'

raw_ts = os.path.join(folder, "Cell_raw.ts")

if os.path.exists(raw_ts):
    ffmpeg_path = r'c:\Users\HP\Downloads\hls live classplus\ffmpeg.exe'
    res = subprocess.run([ffmpeg_path, '-i', raw_ts], capture_output=True, text=True)
    print("--- ffmpeg full stderr ---")
    print(res.stderr)
else:
    print("Cell_raw.ts not found!")
