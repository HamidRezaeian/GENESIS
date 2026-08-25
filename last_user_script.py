import json

transcript_path = r"C:\Users\Hamid\.gemini\antigravity-ide\brain\c733ab59-9b21-413c-9da0-1a35a61f8fc7\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in reversed(lines):
    entry = json.loads(line)
    if entry.get("type") == "USER_INPUT":
        print(f"Step {entry.get('step_index')}:")
        content = entry.get("content", "")
        print(content[:500])
        print("--- TOTAL LEN:", len(content))
        with open("last_user_input.html", "w", encoding="utf-8") as out:
            out.write(content)
        break
