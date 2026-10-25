"""Apply final encoding fixes to opportunity-radar.html."""
import os

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

with open('opportunity-radar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# U+256C (╬) + U+00BD (½) -> μ (mu, U+03BC)
# Context: "Historical Mean (╬╝)" -> should be "Historical Mean (μ)"
old = '\u256c\u00bd'
new = 'μ'
count = content.count(old)

log = []
if count > 0:
    content = content.replace(old, new)
    log.append(f"Fixed U+256C+U+00BD -> mu: {count} times")

# Final verification
remaining_unusual = []
for cp in [0x255D, 0x256C, 0x252C, 0x2556, 0x2592, 0x0393, 0x00C7]:
    char = chr(cp)
    c = content.count(char)
    if c > 0:
        remaining_unusual.append(f"U+{cp:04X} x{c}")

log.append("=== FINAL VERIFICATION ===")
log.append(f"Rupee U+20B9: {content.count(chr(0x20B9))}")
log.append(f"Em-dash U+2014: {content.count(chr(0x2014))}")
log.append(f"En-dash U+2013: {content.count(chr(0x2013))}")
log.append(f"Sigma U+03C3: {content.count(chr(0x03C3))}")
log.append(f"Mu U+03BC: {content.count(chr(0x03BC))}")
log.append(f"Arrow U+2192: {content.count(chr(0x2192))}")
log.append(f"Ellipsis U+2026: {content.count(chr(0x2026))}")
log.append(f"Middle-dot U+00B7: {content.count(chr(0x00B7))}")
log.append(f"Plus-minus U+00B1: {content.count(chr(0x00B1))}")
log.append(f"Remaining unusual: {remaining_unusual if remaining_unusual else 'NONE - CLEAN!'}")

with open('opportunity-radar.html', 'w', encoding='utf-8') as f:
    f.write(content)

with open('final_fix_log.txt', 'w', encoding='utf-8') as f:
    for line in log:
        f.write(line + '\n')

print("Done!")
for line in log:
    print(line)
