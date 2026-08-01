import os
import base64
from Crypto.Cipher import AES

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'

KNOWN_VIDEOS = {
    "Cell _ The Unit Of Life.mp4": "RmwCRlBZEm9BQF4GVxAHR0dvXhRAHlYsHUQXb0NELRzc1mYBcjbT0F4GASwBRRRzWFkSBQARBRQLcV0VEVMDLQVGFCEzREYC",
    "Cell L2.mp4":                  "XFFNRAcWFiIOKy0cAxIeFEdxDEQTU1ctbCp6dlgVEVHc1mYBcjbT0EZQPV0cFhV1XkRGAlBHUUQKdFoVXm1NLVJHRW5CRFxQ",
    "Cell L3.mp4":                  "QmwDEQdBR3APRV0BAy0FKhZ0DFosHFctHUUJcUFZRlDc1mYBcjbT0BICTRMdRRYjX0EtUAARUloJIA1CElJTQlBHESNZKkZs",
}

for name, o1 in KNOWN_VIDEOS.items():
    raw_o1 = base64.b64decode(o1)
    k = raw_o1[:16]
    iv = raw_o1[16:32]
    
    path = os.path.join(folder, name)
    if os.path.exists(path):
        with open(path, "rb") as fh:
            enc = fh.read(16)
        
        # Test IV = o1_iv
        cipher = AES.new(k, AES.MODE_CBC, iv)
        dec_o1 = cipher.decrypt(enc)
        
        # Test IV = zero_iv
        cipher_zero = AES.new(k, AES.MODE_CBC, b'\x00'*16)
        dec_zero = cipher_zero.decrypt(enc)
        
        print(f"File: {name}")
        print(f"  o1 Key: {k.hex()}")
        print(f"  o1 IV : {iv.hex()}")
        print(f"  Dec (o1 IV)  : {dec_o1.hex()} | ts? {dec_o1[0] == 0x47}")
        print(f"  Dec (zero IV): {dec_zero.hex()} | ts? {dec_zero[0] == 0x47}")
        print()
