import os
import glob

folder = r'C:\Users\HP\Downloads'

print("Searching recursively for 'fe2184d0' in Downloads...")

# Recursively find all files
all_files = glob.glob(os.path.join(folder, "**", "*"), recursive=True)

matches = 0
for f in all_files:
    if os.path.isfile(f):
        # Skip media files
        if f.endswith((".mp4", ".ts", ".exe", ".wasm", ".zip", ".7z", ".pdf", ".mp3", ".jfif", ".png", ".jpg", ".jpeg")):
            continue
        try:
            content = open(f, "r", encoding="utf-8", errors="ignore").read()
            if "fe2184d0" in content:
                print(f"FOUND IN: {f}")
                matches += 1
                if matches >= 10:
                    break
        except Exception:
            pass
            
print("Search complete.")
