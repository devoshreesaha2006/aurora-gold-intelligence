"""Fix remaining box chars in opportunity-radar.html."""
import os, re

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

with open('opportunity-radar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# U+252C (┬) + U+2556 (╖) -> middle dot ·  
# Context: "GOLDM ┬╖ latest close:"  -- separator = middle dot
# Also: "z_score)} ┬╖ ${snapshot.percentile_rank}" -- separator = middle dot
# And: "├ not win %" etc.

# U+252C (┬) + U+2592 (▒) -> ± (plus-minus)
# Context: "(┬▒1σ | 68.2%)" -- ±1σ

# What about the I█ we see? Let's find it
iota_chars = {}
for cp in [0x0399, 0x0391, 0x03B9, 0x03B1]:  # Greek iota/alpha etc
    char = chr(cp)
    count = content.count(char)
    if count > 0:
        iota_chars[cp] = count

print("Greek chars remaining:", {hex(k): v for k, v in iota_chars.items()})

# Find all remaining non-ASCII, non-standard chars
unusual = {}
for cp in set(ord(c) for c in content if ord(c) > 127):
    char = chr(cp)
    count = content.count(char)
    # Skip expected/legitimate Unicode chars
    expected = {0x20B9, 0x2014, 0x2013, 0x2022, 0x00B7, 0x00D7, 0x03C3, 0x03BC,
                0x2026, 0x2192, 0x2265, 0x2264, 0x221E, 0x00B1, 0x00B0,
                # Basic Latin supplements that are fine in HTML
                0x00A0, 0x00AB, 0x00BB, 0x00BD, 0x00BE, 0x00BC,
                # Arrows and math
                0x2190, 0x2191, 0x2193, 0x2194, 0x21D2,
                # Other common
                0x00AE, 0x00A9, 0x2122, 0x00E9, 0x00E8, 0x00F1,
                }
    if cp not in expected:
        unusual[cp] = count

with open('remaining_unusual.txt', 'w', encoding='utf-8') as out:
    out.write(f"Unusual chars remaining (after previous fixes):\n")
    for cp, count in sorted(unusual.items()):
        char = chr(cp)
        # Find context
        for i, line in enumerate(content.splitlines(), 1):
            if char in line:
                ctx = line.strip()[:100]
                break
        else:
            ctx = "(no context found)"
        out.write(f"U+{cp:04X} '{char}' x{count}: {ctx}\n")

print("Unusual chars written to remaining_unusual.txt")

# Apply the remaining fixes
replacements = [
    ('\u252c\u2556', '\u00b7'),   # ┬╖ -> · (middle dot)
    ('\u252c\u2592', '\u00b1'),   # ┬▒ -> ± (plus-minus)
]

log = []
for old, new in replacements:
    count = content.count(old)
    if count > 0:
        content = content.replace(old, new)
        log.append(f"Replaced U+{ord(old[0]):04X}+U+{ord(old[1]):04X} -> U+{ord(new):04X}: {count} times")
        print(log[-1])

# Write the fixed file
with open('opportunity-radar.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nMiddle dot U+00B7 count: {content.count(chr(0x00B7))}")
print(f"Plus-minus U+00B1 count: {content.count(chr(0x00B1))}")
print(f"Box-252C remaining: {content.count(chr(0x252C))}")
print("File written!")
