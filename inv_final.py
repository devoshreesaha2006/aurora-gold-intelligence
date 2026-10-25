"""Fix the last remaining corrupted chars in opportunity-radar.html."""
import os, re

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

with open('opportunity-radar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remaining issues from remaining_unusual.txt:
# U+255D (╝) in "Historical Mean (╝╬?)" -> should be μ (mu) + σ (sigma) = "Historical Mean (μ ± Xσ)"
# U+256C (╬) in same context
# U+2592 (▒) in "Normal Equilibrium Zone (±1▒σ | 68.2%)" -- the ▒ here should be nothing (already have ±1σ)
# Wait, the ┬▒ pattern was ± and now the 2592 alone must be something else

# Let's find all remaining unusual chars carefully
for cp in [0x255D, 0x256C, 0x2592, 0x2556]:
    char = chr(cp)
    count = content.count(char)
    if count > 0:
        for i, line in enumerate(content.splitlines(), 1):
            if char in line:
                with open(f'ctx_{cp:04X}.txt', 'w', encoding='utf-8') as f:
                    f.write(f"U+{cp:04X} x{count}\n")
                    for j, ln in enumerate(content.splitlines(), 1):
                        if char in ln:
                            f.write(f"  Line {j}: {ln.strip()[:150]}\n")
                break

# From context analysis:
# "Normal Equilibrium Zone (±1▒σ | 68.2%)" - the ▒ is leftover from ┬▒ that wasn't caught
# Actually wait: ┬▒ (252C + 2592) was ±, so ▒ alone (2592) must be something else
# "Historical Mean (╝╬?)" context = U+255D + U+256C -> this was probably μ
# These look like "μ" (U+03BC) was corrupted 

# Let me check what's around ╝╬:
idx = content.find(chr(0x255D) + chr(0x256C))
if idx >= 0:
    ctx = content[max(0,idx-30):idx+40]
    print(f"255D+256C context: {repr(ctx)}")

# And standalone 2592:
for m in re.finditer(re.escape(chr(0x2592)), content):
    ctx = content[max(0,m.start()-20):m.start()+30]
    print(f"2592 context: {repr(ctx)}")

# And 2556:
for m in re.finditer(re.escape(chr(0x2556)), content):
    ctx = content[max(0,m.start()-20):m.start()+30]
    print(f"2556 context: {repr(ctx)}")
