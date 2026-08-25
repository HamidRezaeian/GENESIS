import json

transcript_path = r"C:\Users\Hamid\.gemini\antigravity-ide\brain\c733ab59-9b21-413c-9da0-1a35a61f8fc7\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

u = [json.loads(l) for l in lines if json.loads(l).get("type") == "USER_INPUT"]
print(f"Total user inputs: {len(u)}")

# Get the previous one before current
if len(u) >= 2:
    prev = u[-2]
    print("Step index:", prev.get("step_index"))
    content = prev.get("content", "")
    print("Length:", len(content))
    with open(r"C:\Users\Hamid\source\repos\GENESIS\prev_user_input.txt", "w", encoding="utf-8") as out:
        out.write(content)
    print("Saved to prev_user_input.txt")
