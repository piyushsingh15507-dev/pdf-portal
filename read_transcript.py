import os
import json

log_path = r'C:\Users\HP\.gemini\antigravity\brain\d4f512f9-410e-4ba4-9415-4f17bc632edd\.system_generated\logs\transcript.jsonl'

if os.path.exists(log_path):
    print("Reading log...")
    matches = 0
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                content = str(data.get("content", ""))
                # Search for o1, Kinematics, key, or iv
                if any(x in content for x in ["Kinematics", "o1=", "Key verified"]):
                    print(f"Step {data.get('step_index')}: {content[:200]}")
                    matches += 1
                    if matches >= 30:
                        break
            except Exception as e:
                pass
else:
    print("Transcript not found at", log_path)
