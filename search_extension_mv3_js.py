import os
import glob

ext_dir = r'C:\Users\HP\Downloads\extension-mv3-chrome'

js_files = glob.glob(os.path.join(ext_dir, "**", "*.js"), recursive=True)

print(f"Searching in {len(js_files)} JS files:\n")
for f in js_files:
    rel_path = os.path.relpath(f, ext_dir)
    try:
        content = open(f, encoding='utf-8', errors='ignore').read()
    except Exception as e:
        print(f"Failed to read {rel_path}: {e}")
        continue
    
    # Print lines with matches
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if any(x in line.lower() for x in ["classplus", "o1=", "o1_key", "o1_iv"]):
            print(f"{rel_path}:{idx+1}: {line.strip()[:140]}")
