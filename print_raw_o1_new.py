import base64

o1_val = "LW1RR1EqRnEPFUAdTBAGQXp2WCtCAQFdHUB6IzIWRwbc1mYBcjbT0BNQTlxTRQpyWkJBHFYsUhVEIVwUQQFXQh1Be3FDRS1Q"
raw = base64.b64decode(o1_val)

print("Total raw bytes:", len(raw))
print("Hex representation:")
print(raw.hex())

for i in range(0, len(raw), 16):
    chunk = raw[i:i+16]
    print(f"Block {i//16}: {chunk.hex()} | {chunk}")
