import os

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'

patched_playlist = os.path.join(folder, "_patched_playlist.m3u8")

if os.path.exists(patched_playlist):
    print("--- _patched_playlist.m3u8 lines containing KEY ---")
    with open(patched_playlist, "r", encoding="utf-8") as f:
        for line in f:
            if "KEY" in line:
                print(line.strip())
else:
    print("_patched_playlist.m3u8 not found!")
