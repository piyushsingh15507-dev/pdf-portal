import os
import json

log_path = r'C:\Users\HP\.gemini\antigravity\brain\d4f512f9-410e-4ba4-9415-4f17bc632edd\.system_generated\logs\transcript.jsonl'

if os.path.exists(log_path):
    print("Searching log for real key origin...")
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                content = str(data.get("content", ""))
                # Also check tool_calls
                tool_calls = str(data.get("tool_calls", ""))
                if "fe2184d" in content or "fe2184d" in tool_calls:
                    print(f"Step {data.get('step_index')} ({data.get('type')}):")
                    # Print context of match
                    idx = content.find("fe2184d")
                    if idx != -1:
                        print("Content snippet:", content[max(0, idx-200):idx+300])
                    else:
                        print("Tool calls snippet:", tool_calls[:500])
                    print("-" * 50)
            except Exception as e:
                pass
else:
    print("Transcript not found")
