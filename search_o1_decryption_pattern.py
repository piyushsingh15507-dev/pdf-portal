import base64
from Crypto.Cipher import AES

o1_val = "LW1RR1EqRnEPFUAdTBAGQXp2WCtCAQFdHUB6IzIWRwbc1mYBcjbT0BNQTlxTRQpyWkJBHFYsUhVEIVwUQQFXQh1Be3FDRS1Q"
raw = base64.b64decode(o1_val)

b0 = raw[0:16]   # o1_key
b1 = raw[16:32]  # o1_iv
b2 = raw[32:48]
b3 = raw[48:64]
b4 = raw[64:72]

real_key = bytes.fromhex("fe2184d0b17163c4ad4336f32e6504a7")

print("b0:       ", b0.hex())
print("b1:       ", b1.hex())
print("b2:       ", b2.hex())
print("b3:       ", b3.hex())
print("b4:       ", b4.hex())
print("real_key: ", real_key.hex())
print()

# Test 1: Simple XOR of blocks
# Let's check if real_key is a combination of XORs
print("--- Test 1: XOR combinations ---")
for name, block in [("b0", b0), ("b1", b1), ("b2", b2), ("b3", b3)]:
    xor_res = bytes(x ^ y for x, y in zip(real_key, block))
    print(f"real_key ^ {name}: {xor_res.hex()}")

# Test 2: AES decryption of b0 using different blocks as Key/IV
print("\n--- Test 2: AES Decryption ---")
blocks = [b0, b1, b2, b3]
block_names = ["b0", "b1", "b2", "b3"]

for i in range(4):
    for j in range(4):
        if i == j: continue
        k = blocks[i]
        iv = blocks[j]
        # Decrypt b2
        cipher = AES.new(k, AES.MODE_CBC, iv)
        try:
            dec = cipher.decrypt(b2)
            if dec == real_key:
                print(f"[✓] SUCCESS! Decrypting b2 using Key={block_names[i]}, IV={block_names[j]} yields real_key!")
        except Exception:
            pass
            
        # Decrypt b3
        cipher = AES.new(k, AES.MODE_CBC, iv)
        try:
            dec = cipher.decrypt(b3)
            if dec == real_key:
                print(f"[✓] SUCCESS! Decrypting b3 using Key={block_names[i]}, IV={block_names[j]} yields real_key!")
        except Exception:
            pass
            
        # Decrypt b0 (using zero IV or other IVs)
        # What if b0 is decrypted?
        cipher = AES.new(k, AES.MODE_CBC, iv)
        try:
            dec = cipher.decrypt(b0)
            if dec == real_key:
                print(f"[✓] SUCCESS! Decrypting b0 using Key={block_names[i]}, IV={block_names[j]} yields real_key!")
        except Exception:
            pass

# Test 3: What if we decrypt the whole o1 payload starting from byte 32?
# The payload length is 72 bytes. The first 32 bytes are b0 and b1 (used as Key and IV).
# The remaining bytes are 40 bytes (b2 + b3 + b4).
# In CBC mode, decrypting 40 bytes (with padding) will yield 40 decrypted bytes.
# Let's decrypt raw[32:] using Key=b0, IV=b1!
print("\n--- Test 3: Decrypting tail raw[32:] with b0 and b1 ---")
try:
    # CBC requires multiple of 16. raw[32:] is 40 bytes (not multiple of 16).
    # Wait, let's pad raw[32:] or take the first 32 bytes of it (b2 + b3).
    tail = raw[32:64] # 32 bytes
    cipher = AES.new(b0, AES.MODE_CBC, b1)
    dec = cipher.decrypt(tail)
    print("Decrypted tail (32 bytes):", dec.hex())
    print("Decrypted block 0 (16 bytes):", dec[:16].hex())
    print("Decrypted block 1 (16 bytes):", dec[16:32].hex())
    if dec[:16] == real_key:
        print("[✓] SUCCESS! The first 16 bytes of decrypted tail is the real_key!")
    if dec[16:32] == real_key:
        print("[✓] SUCCESS! The second 16 bytes of decrypted tail is the real_key!")
except Exception as e:
    print("Error:", e)
