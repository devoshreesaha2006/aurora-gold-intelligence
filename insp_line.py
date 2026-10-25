"""Inspect line 3138 of opportunity-radar.html for exact char sequence."""
import os
os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

with open('opportunity-radar.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
line = lines[3137]  # 0-indexed

chars_info = []
for i, c in enumerate(line):
    if ord(c) > 127:
        chars_info.append(f"pos {i}: U+{ord(c):04X}")

with open('line3138.txt', 'w', encoding='utf-8') as f:
    f.write(f"Line 3138 (0-indexed 3137):\n")
    f.write(line)
    f.write("\n\nNon-ASCII chars:\n")
    for ci in chars_info:
        f.write(ci + '\n')
    
    # Find the specific "╬╝" sequence
    idx = line.find('\u256c')
    if idx >= 0:
        seq = line[idx:idx+5]
        f.write(f"\nFound U+256C at pos {idx}\n")
        f.write(f"Following chars: {' '.join(f'U+{ord(c):04X}' for c in seq)}\n")

print("Done - see line3138.txt")
