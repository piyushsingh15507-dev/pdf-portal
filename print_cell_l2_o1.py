import base64

o1_val = "XFFNRAcWFiIOKy0cAxIeFEdxDEQTU1ctbCp6dlgVEVHc1mYBcjbT0EZQPV0cFhV1XkRGAlBHUUQKdFoVXm1NLVJHRW5CRFxQ"
raw = base64.b64decode(o1_val)

print("Total raw bytes:", len(raw))
for i in range(0, len(raw), 16):
    chunk = raw[i:i+16]
    print(f"Block {i//16}: {chunk.hex()} | {chunk}")
