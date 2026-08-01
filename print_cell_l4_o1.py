import base64

o1_val = "EB1WEVFBR3YPK0FRAkIDRUdxXURdAVEsUkF7dVpZRhzc1mYBcjbT0ENtPFwDWnseDFssHgNDUBRFHjJELB4DR1IXRXBeWkAF"
raw = base64.b64decode(o1_val)

print("Total raw bytes:", len(raw))
for i in range(0, len(raw), 16):
    chunk = raw[i:i+16]
    print(f"Block {i//16}: {chunk.hex()} | {chunk}")
