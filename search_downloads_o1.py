import os

folder = r'C:\Users\HP\Downloads'
for f in os.listdir(folder):
    if f.endswith(".py"):
        path = os.path.join(folder, f)
        try:
            content = open(path, encoding='utf-8', errors='ignore').read()
            if 'o1' in content:
                print(f"Match in file: {f}")
                # Print matching lines
                for idx, line in enumerate(content.splitlines()):
                    if 'o1' in line:
                        print(f"  Line {idx+1}: {line.strip()[:140]}")
        except Exception as e:
            pass
