"""Investigate remaining U+252C box-drawing chars in opportunity-radar.html."""
import os, re

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

with open('opportunity-radar.html', 'r', encoding='utf-8') as f:
    content = f.read()

char = chr(0x252C)  # BOX DRAWINGS LIGHT DOWN AND HORIZONTAL ┬

positions = [m.start() for m in re.finditer(re.escape(char), content)]

with open('box252c.txt', 'w', encoding='utf-8') as out:
    out.write(f"U+252C occurrences: {len(positions)}\n\n")
    for pos in positions[:30]:
        next_char = content[pos+1] if pos+1 < len(content) else ''
        ctx = content[max(0, pos-20):pos+30]
        out.write(f"pos={pos} next=U+{ord(next_char):04X} {repr(next_char)}\n")
        out.write(f"  ctx: {repr(ctx)}\n\n")

print("Done - see box252c.txt")
