import os
import subprocess

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'

dec_file = os.path.join(folder, "Cell L3_decrypted.mp4")

if os.path.exists(dec_file):
    ffmpeg_path = r'c:\Users\HP\Downloads\hls live classplus\ffmpeg.exe'
    res = subprocess.run([ffmpeg_path, '-i', dec_file], capture_output=True, text=True)
    print("--- ffmpeg full stderr ---")
    print(res.stderr)
else:
    print("Cell L3_decrypted.mp4 not found!")
