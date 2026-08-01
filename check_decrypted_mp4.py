import os

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'

enc_file = os.path.join(folder, "Cell _ The Unit Of Life.mp4")
dec_file = os.path.join(folder, "Cell _ The Unit Of Life_decrypted.mp4")

if os.path.exists(enc_file):
    with open(enc_file, "rb") as f:
        head_enc = f.read(32)
    print("Encrypted MP4 Header (Hex):", head_enc.hex())

if os.path.exists(dec_file):
    with open(dec_file, "rb") as f:
        head_dec = f.read(32)
    print("Decrypted MP4 Header (Hex):", head_dec.hex())
    print("Decrypted MP4 Header (Ascii):", head_dec)
