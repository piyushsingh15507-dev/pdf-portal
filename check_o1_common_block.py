import base64

KNOWN_VIDEOS = {
    "Cell _ The Unit Of Life": "RmwCRlBZEm9BQF4GVxAHR0dvXhRAHlYsHUQXb0NELRzc1mYBcjbT0F4GASwBRRRzWFkSBQARBRQLcV0VEVMDLQVGFCEzREYC",
    "Cell L2":                  "XFFNRAcWFiIOKy0cAxIeFEdxDEQTU1ctbCp6dlgVEVHc1mYBcjbT0EZQPV0cFhV1XkRGAlBHUUQKdFoVXm1NLVJHRW5CRFxQ",
    "Cell L3":                  "QmwDEQdBR3APRV0BAy0FKhZ0DFosHFctHUUJcUFZRlDc1mYBcjbT0BICTRMdRRYjX0EtUAARUloJIA1CElJTQlBHESNZKkZs",
    "Cell L4":                  "EB1WEVFBR3YPK0FRAkIDRUdxXURdAVEsUkF7dVpZRhzc1mYBcjbT0ENtPFwDWnseDFssHgNDUBRFHjJELB4DR1IXRXBeWkAF",
    "Cell L8":                  "RxxMRwUXenZYW11QAl8GFhUhDERdbFZAAkBGIlpGRlDc1mYBcjbT0BMGUxEAWhRyQhVcUE1cHBYSdVwUQB1SQgNHEW9aQBEB",
    "New Video":                "LW1RR1EqRnEPFUAdTBAGQXp2WCtCAQFdHUB6IzIWRwbc1mYBcjbT0BNQTlxTRQpyWkJBHFYsUhVEIVwUQQFXQh1Be3FDRS1Q"
}

for name, o1 in KNOWN_VIDEOS.items():
    raw = base64.b64decode(o1)
    print(f"Name: {name}")
    print(f"  Length: {len(raw)} bytes")
    # Find dcd666017236d3d0
    idx = raw.hex().find("dcd666017236d3d0")
    if idx != -1:
        print(f"  dcd666017236d3d0 found at byte index: {idx//2}")
        # Print blocks of 16 bytes
        for b in range(0, len(raw), 16):
            chunk = raw[b:b+16]
            print(f"    Block {b//16}: {chunk.hex()} | {chunk}")
    else:
        print("  Common hex not found!")
    print()
