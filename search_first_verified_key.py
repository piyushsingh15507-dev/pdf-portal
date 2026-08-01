import os
import json

log_path = r'C:\Users\HP\.gemini\antigravity\brain\d4f512f9-410e-4ba4-9415-4f17bc632edd\.system_generated\logs\transcript.jsonl'

if os.path.exists(log_path):
    print("Searching log for verified key...")
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                content = str(data.get("content", ""))
                tool_calls = str(data.get("tool_calls", ""))
                if "405155" in content or "405155" in tool_calls:
                    print(f"Step {data.get('step_index')} ({data.get('type')}):")
                    idx = content.find("405155")
                    if idx != -1:
                        print("Content snippet:", content[max(0, idx-100):idx+300])
                    else:
                        print("Tool calls snippet:", tool_calls[:500])
                    print("-" * 50)
            except Exception:
                pass
else:
    print("Transcript not found")
