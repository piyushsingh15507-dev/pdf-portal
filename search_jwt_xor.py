o1_key = bytes.fromhex("466c02465059126f41405e0657100747")
key_bin = bytes.fromhex("426c0311074147700f455d01032d052a")

# The XOR pattern we are searching for:
xor_target = bytes(a ^ b for a, b in zip(o1_key, key_bin))
print("Target XOR Pattern (Hex):", xor_target.hex())

# Active JWT token from user (the old one used when Course_840821 was active)
# Wait, let's search in the old token from the first checkpoint!
token = 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTgyNTIzNTc0LCJvcmdJZCI6Mjk3NzUyLCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTg4NDc0MjAwMzgiLCJuYW1lIjoiRHJpc2h0aSIsImVtYWlsIjoiZm9ybW1haWw5MTJAZ21haWwuY29tIiwiaXNJbnRlcm5hdGlvbmFsIjowLCJkZWZhdWx0TGFuZ3VhZ2UiOiJFTiIsImNvdW50cnlDb2RlIjoiSU4iLCJjb3VudHJ5SVNPIjoiOTEiLCJ0aW1lem9uZSI6IkdNVCs1OjMwIiwiaXNEaXkiOnRydWUsIm9yZ0NvZGUiOiJ2b2FhZiIsImlzRGl5U3ViYWRtaW4iOjAsImZpbmdlcnByaW50SWQiOiIyM2Q4ZGI4YjhhYThmZDMwNjU3OTQzMGRkOTUxZjk0YiIsImlhdCI6MTc4NTQxNjIzNCwiZXhwIjoxNzg2MDIxMDM0fQ.RTkdTRfNosogL2aPceUWLQk7bi5Aaqf47RsD2JF5TpXV1_6h26QDzyOzfRGRnCnC'

token_bytes = token.encode('utf-8')

# Search for the XOR target pattern in the token by shifting a window
found = False
for i in range(len(token_bytes) - 15):
    window = token_bytes[i:i+16]
    # Check if this window XORed with o1_key gives key_bin
    # Wait, we know xor_target is the exact XOR of o1_key and key_bin.
    # So the window must be equal to xor_target!
    # But xor_target contains binary bytes (like 0x04, 0x00, 0x01) which are not valid base64 chars.
    # So the token (which is base64) cannot contain xor_target directly.
    pass

# But what if the o1_key itself is XORed with a hash of the token, or some other key?
# Wait! Let's check if the o1_key needs to be decrypted using a fixed key?
# Classplus app code has a decryption key.
# Let's search the web for "Classplus decryption algorithm" or "decode_o1" or similar in other repos.
