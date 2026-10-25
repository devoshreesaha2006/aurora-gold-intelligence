"""Final comprehensive check of opportunity-radar.html character state."""
import os

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

with open('opportunity-radar.html', 'r', encoding='utf-8') as f:
    content = f.read()

with open('final_char_audit.txt', 'w', encoding='utf-8') as out:
    # Box drawing chars
    box_drawing = sorted(set(c for c in content if 0x2500 <= ord(c) <= 0x259F))
    out.write(f"Box drawing chars remaining: {[f'U+{ord(c):04X}' for c in box_drawing]}\n\n")
    
    # All non-ASCII
    special = {}
    for c in content:
        cp = ord(c)
        if cp > 127:
            special[cp] = special.get(cp, 0) + 1
    
    out.write("All non-ASCII chars:\n")
    expected_ok = {
        0x00A0: 'non-breaking space',
        0x00B7: 'middle dot',
        0x00B1: 'plus-minus',
        0x00D7: 'multiplication',
        0x2014: 'em-dash',
        0x2013: 'en-dash',
        0x2022: 'bullet',
        0x2026: 'ellipsis',
        0x2192: 'right arrow',
        0x2190: 'left arrow',
        0x2191: 'up arrow',
        0x2193: 'down arrow',
        0x2265: 'geq',
        0x2264: 'leq',
        0x00B0: 'degree',
        0x00AE: 'registered',
        0x03C3: 'sigma',
        0x03BC: 'mu',
        0x20B9: 'rupee',
        0x221E: 'infinity',
        0x00B2: 'superscript 2',
        0x00B3: 'superscript 3',
    }
    
    suspicious = []
    for cp, count in sorted(special.items()):
        name = expected_ok.get(cp, 'UNKNOWN')
        marker = '' if cp in expected_ok else '  <-- CHECK'
        out.write(f"  U+{cp:04X} '{chr(cp)}' x{count}: {name}{marker}\n")
        if cp not in expected_ok:
            suspicious.append((cp, count, name))
    
    out.write(f"\nSuspicious chars: {len(suspicious)}\n")
    if not suspicious:
        out.write("ALL CLEAR - No suspicious characters!\n")
    
    # Key counts
    out.write("\n=== KEY CHAR COUNTS ===\n")
    for cp, name in sorted(expected_ok.items()):
        if cp in special:
            out.write(f"  {name}: {special[cp]}\n")

print("Done - see final_char_audit.txt")
