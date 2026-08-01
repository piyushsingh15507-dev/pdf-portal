import base64

o1 = "RmwCRlBZEm9BQF4GVxAHR0dvXhRAHlYsHUQXb0NELRzc1mYBcjbT0F4GASwBRRRzWFkSBQARBRQLcV0VEVMDLQVGFCEzREYC"
raw = base64.b64decode(o1)

print("Total raw bytes:", len(raw))
print("Hex representation:")
print(raw.hex())

# Split into 16-byte blocks
for i in range(0, len(raw), 16):
    chunk = raw[i:i+16]
    print(f"Block {i//16}: {chunk.hex()} | {chunk}")
