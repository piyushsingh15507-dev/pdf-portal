import os

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'

playlist_path = os.path.join(folder, "_playlist.m3u8")
patched_path = os.path.join(folder, "_patched_playlist.m3u8")

if os.path.exists(playlist_path):
    print("--- _playlist.m3u8 (First 15 lines) ---")
    with open(playlist_path, "r", encoding="utf-8") as f:
        content = f.read().splitlines()
    for i in range(min(15, len(content))):
        print(f"{i+1:02d}: {content[i]}")

if os.path.exists(patched_path):
    print("\n--- _patched_playlist.m3u8 (First 15 lines) ---")
    with open(patched_path, "r", encoding="utf-8") as f:
        content = f.read().splitlines()
    for i in range(min(15, len(content))):
        print(f"{i+1:02d}: {content[i]}")
