import os
import json

log_path = r'C:\Users\HP\.gemini\antigravity\brain\d4f512f9-410e-4ba4-9415-4f17bc632edd\.system_generated\logs\transcript_full.jsonl'

if os.path.exists(log_path):
    print("Searching full log for Classplus_Video...")
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                content = str(data.get("content", ""))
                tool_calls = str(data.get("tool_calls", ""))
                if "Classplus_Video" in content or "Classplus_Video" in tool_calls:
                    print(f"Step {data.get('step_index')} ({data.get('type')}):")
                    idx = content.find("Classplus_Video")
                    if idx != -1:
                        print("Content snippet:", content[max(0, idx-100):idx+300])
                    else:
                        print("Tool calls snippet:", tool_calls[:300])
                    print("-" * 50)
            except Exception:
                pass
else:
    print("Transcript not found")
