import os
import json

log_path = r'C:\Users\HP\.gemini\antigravity\brain\d4f512f9-410e-4ba4-9415-4f17bc632edd\.system_generated\logs\transcript_full.jsonl'

if os.path.exists(log_path):
    print("Reading full log for Step 203...")
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get("step_index") == 203:
                    # Print the entire tool calls or content
                    print(json.dumps(data.get("tool_calls"), indent=2))
                    break
            except Exception as e:
                pass
else:
    print("transcript_full.jsonl not found!")
