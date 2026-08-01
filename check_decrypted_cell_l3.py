import os

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'
dec_file = os.path.join(folder, "Cell L3_decrypted.mp4")

if os.path.exists(dec_file):
    with open(dec_file, "rb") as f:
        head = f.read(16)
    print("Decrypted Cell L3 Header (Hex):", head.hex())
    if head[0] == 0x47:
        print("[✓] Starts with 0x47 (MPEG-TS Sync Byte)!")
    else:
        print("[X] Does not start with 0x47.")
else:
    print("Cell L3_decrypted.mp4 not found!")
