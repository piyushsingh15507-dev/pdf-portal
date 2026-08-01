import os
import glob

ext_dir = r'C:\Users\HP\Downloads\Xtream-Masters_CDM_Decryptor_Extension_v3.7.54'

js_files = glob.glob(os.path.join(ext_dir, "**", "*.js"), recursive=True)

print(f"Searching in {len(js_files)} JS files:\n")
for f in js_files:
    rel_path = os.path.relpath(f, ext_dir)
    lines = open(f, encoding='utf-8', errors='ignore').readlines()
    for idx, line in enumerate(lines):
        if any(x in line.lower() for x in ["classplus", "o1", "encn", "aes"]):
            print(f"{rel_path}:{idx+1}: {line.strip()[:120]}")
