import os

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'

for f in ["Cell L2.mp4", "Cell L3.mp4", "Cell _ The Unit Of Life.mp4"]:
    path = os.path.join(folder, f)
    if os.path.exists(path):
        with open(path, "rb") as fh:
            head = fh.read(16)
        print(f"File: {f} | Size: {os.path.getsize(path)/(1024*1024):.1f} MB | Header (Hex): {head.hex()}")
