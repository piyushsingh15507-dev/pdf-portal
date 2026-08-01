o1_key  = bytes.fromhex("466c02465059126f41405e0657100747")
o1_iv   = bytes.fromhex("476f5e14401e562c1d44176f43442d1c")
key_bin = bytes.fromhex("426c0311074147700f455d01032d052a")
aes_key = bytes.fromhex("5c514d44071616220e2b2d1c03121e14")

print("key_bin XOR aes_key:", bytes(a ^ b for a, b in zip(key_bin, aes_key)).hex())
print("o1_key XOR key_bin :", bytes(a ^ b for a, b in zip(o1_key, key_bin)).hex())
print("o1_key XOR aes_key :", bytes(a ^ b for a, b in zip(o1_key, aes_key)).hex())
print("o1_iv  XOR aes_key :", bytes(a ^ b for a, b in zip(o1_iv, aes_key)).hex())

# Let's check if there is an XOR key of length 16 that is commonly used in Classplus
# The word could be "classplus", "classplusapp", etc.
for word in ["classplus", "classplusapp", "classplusvideo", "voaaf", "drishti", "297752", "182523574"]:
    word_bytes = word.encode('utf-8')
    # Pad to 16 bytes
    word_bytes = word_bytes + b'\x00' * (16 - len(word_bytes))
    print(f"\nXOR with '{word}':")
    print("o1_key XOR word :", bytes(a ^ b for a, b in zip(o1_key, word_bytes)).hex())
    print("key_bin XOR word:", bytes(a ^ b for a, b in zip(key_bin, word_bytes)).hex())
