import os
import glob

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'

pattern_bin = os.path.join(folder, "*.bin")
pattern_key = os.path.join(folder, "*.key")

files = glob.glob(pattern_bin) + glob.glob(pattern_key)

print(f"Found {len(files)} key/bin files:\n")
for f in files:
    name = os.path.basename(f)
    size = os.path.getsize(f)
    with open(f, "rb") as fh:
        data = fh.read()
    print(f"File: {name} ({size} bytes)")
    print(f"  Hex: {data.hex()}")
    print()
