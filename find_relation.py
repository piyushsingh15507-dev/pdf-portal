o1_key = bytes.fromhex("466c02465059126f41405e0657100747")
o1_iv  = bytes.fromhex("476f5e14401e562c1d44176f43442d1c")

# In the Lecture Recordings folder:
key_bin = bytes.fromhex("426c0311074147700f455d01032d052a")
aes_key = bytes.fromhex("5c514d44071616220e2b2d1c03121e14")

print("--- XOR relations ---")
# Check if key_bin is XORed with o1_key or o1_iv
xor_key = bytes(a ^ b for a, b in zip(o1_key, key_bin))
print("o1_key XOR key_bin :", xor_key.hex())

xor_iv = bytes(a ^ b for a, b in zip(o1_iv, key_bin))
print("o1_iv  XOR key_bin :", xor_iv.hex())

xor_aes_key = bytes(a ^ b for a, b in zip(o1_key, aes_key))
print("o1_key XOR aes_key :", xor_aes_key.hex())

# Let's check AES decryption of aes_key using o1_key and o1_iv
from Crypto.Cipher import AES
try:
    cipher = AES.new(o1_key, AES.MODE_CBC, o1_iv)
    dec = cipher.decrypt(aes_key)
    print("\nAES CBC Decrypt(aes_key):", dec.hex())
except Exception as e:
    print("AES decrypt failed:", e)
