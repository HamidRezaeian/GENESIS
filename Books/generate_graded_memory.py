import random
import os

def generate_graded_memory(filename, total_lines=500):
    delays = [1, 2, 4, 8, 16, 24, 32, 40]
    lines_per_stage = total_lines // len(delays)
    
    random.seed(42)  # For reproducibility
    
    content = []
    
    for delay in delays:
        for _ in range(lines_per_stage):
            if random.choice([True, False]):
                cue = "a"
                ans = "A"
            else:
                cue = "b"
                ans = "B"
                
            import string
            # Use random digits and punctuation to prevent farming predictable dots AND avoid colliding with a,b,A,B
            noise_chars = string.digits + string.punctuation
            dots = "".join(random.choice(noise_chars) for _ in range(delay))
            line = f"{cue}{dots}{ans}"
            content.append(line)
            
    # Write to file
    with open(filename, "w") as f:
        f.write("\n".join(content) + "\n")
        
    print(f"Generated {len(content)} lines in {filename} with max delay {delays[-1]}")

if __name__ == "__main__":
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Diagnostic", "GradedMemory.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    generate_graded_memory(out_path)
