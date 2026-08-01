import os
import base64

o1_val = "RmwCRlBZEm9BQF4GVxAHR0dvXhRAHlYsHUQXb0NELRzc1mYBcjbT0F4GASwBRRRzWFkSBQARBRQLcV0VEVMDLQVGFCEzREYC"

# Base64 decode o1
raw = base64.b64decode(o1_val)
o1_key = raw[:16]
o1_iv = raw[16:32]

print("--- Decoded from o1 parameter ---")
print("o1 Key (Hex):", o1_key.hex())
print("o1 IV (Hex) :", o1_iv.hex())

# Now check the files in the directory
folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'

key_bin_path = os.path.join(folder, "_key.bin")
aes_key_path = os.path.join(folder, "_aes_key.bin")

if os.path.exists(key_bin_path):
    with open(key_bin_path, "rb") as f:
        key_bytes = f.read()
    print("\n--- _key.bin contents ---")
    print("Length:", len(key_bytes))
    print("Hex   :", key_bytes.hex())

if os.path.exists(aes_key_path):
    with open(aes_key_path, "rb") as f:
        aes_bytes = f.read()
    print("\n--- _aes_key.bin contents ---")
    print("Length:", len(aes_bytes))
    print("Hex   :", aes_bytes.hex())
