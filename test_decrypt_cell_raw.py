import os
import subprocess
from Crypto.Cipher import AES

o1 = "RmwCRlBZEm9BQF4GVxAHR0dvXhRAHlYsHUQXb0NELRzc1mYBcjbT0F4GASwBRRRzWFkSBQARBRQLcV0VEVMDLQVGFCEzREYC"

# Base64 decode o1 to get key and IV
import base64
raw = base64.b64decode(o1)
key = raw[:16]
iv = raw[16:32]

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'
src = os.path.join(folder, "Cell_raw.ts")
dst = "Cell_raw_decrypted.ts"

if os.path.exists(src):
    print("Decrypting Cell_raw.ts...")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    with open(src, "rb") as fin, open(dst, "wb") as fout:
        while True:
            chunk = fin.read(1024 * 1024)
            if not chunk:
                break
            if len(chunk) % 16 != 0:
                chunk += b'\x00' * (16 - len(chunk) % 16)
            fout.write(cipher.decrypt(chunk))
            
    print("Decryption finished. Running ffmpeg...")
    ffmpeg_path = r'c:\Users\HP\Downloads\hls live classplus\ffmpeg.exe'
    res = subprocess.run([ffmpeg_path, '-i', dst], capture_output=True, text=True)
    print("\n--- ffmpeg stderr ---")
    print(res.stderr)
    
    # Clean up
    if os.path.exists(dst):
        os.remove(dst)
else:
    print("Cell_raw.ts not found!")
