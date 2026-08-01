import os
import json

log_path = r'C:\Users\HP\.gemini\antigravity\brain\d4f512f9-410e-4ba4-9415-4f17bc632edd\.system_generated\logs\transcript.jsonl'

if os.path.exists(log_path):
    print("Reading log for KEY SERVER info...")
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                content = str(data.get("content", ""))
                if "KEY SERVER" in content or "REAL KEY" in content or "real_key_bytes" in content:
                    print(f"Step {data.get('step_index')}:")
                    print(content[:500])
                    print("-" * 50)
            except Exception:
                pass
else:
    print("Transcript not found")
