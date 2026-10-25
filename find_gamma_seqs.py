"""Compare opportunity-radar.html with aurora-pipeline.js to understand the correct chars."""
import os, re

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

# The key insight from map_analysis.txt:
# ΓÇö (0393 00C7 00F6) appears in:
#   - title: "AURORA ΓÇö Opportunity Radar" -> should be "AURORA — Opportunity Radar" (em-dash)
#   - "GN SYSTEM ΓÇö NAVY / GOLD / CLAY" -> should be "— NAVY / GOLD / CLAY"
#   - ticker-price">ΓÇö</span> -> should be "—" (placeholder)
#   - "As of ΓÇö</span>" -> should be "—" (placeholder date)
#   - "backend dataΓÇê" -> Ç + ê = different ending
#   - "(0 ΓÇô 100 Scale)" -> should be "(0 — 100 Scale)" (en-dash or em-dash)
#   - "Opportunity Score (0ΓÇô100)" -> should be "(0—100)"
#   - "Pairwise Spread Matrix (Γé╣ / 10g)" -> Γé╣ should be ₹ (rupee)

# So the mapping is:
# ΓÇö -> — (em-dash U+2014) -- BUT ONLY WHEN USED AS SEPARATOR
# ΓÇô -> — (en-dash or em-dash between numbers)  
# Γé╣ -> ₹ (rupee sign U+20B9)
# ΓÇó -> • (bullet U+2022)
# Γü -> → or ↑ (arrows)

# Let me find ALL unique Gamma-starting sequences and their contexts
with open('opportunity-radar.html', 'r', encoding='utf-8') as f:
    content = f.read()

gamma = chr(0x0393)
sequences = {}

for m in re.finditer(re.escape(gamma) + r'.{0,3}', content):
    seq = m.group()
    ctx = content[max(0, m.start()-20):m.start()+40]
    if seq not in sequences:
        sequences[seq] = []
    sequences[seq].append(ctx)

with open('gamma_map.txt', 'w', encoding='utf-8') as out:
    out.write(f"All Gamma-starting sequences in opportunity-radar.html:\n\n")
    for seq, contexts in sorted(sequences.items()):
        seq_hex = ' '.join(f'U+{ord(c):04X}' for c in seq)
        out.write(f"Sequence: {repr(seq)} ({seq_hex}) - {len(contexts)} occurrences\n")
        for ctx in contexts[:3]:
            out.write(f"  Context: {repr(ctx)}\n")
        out.write("\n")

print(f"Found {len(sequences)} unique Gamma-starting sequences")
for seq in sorted(sequences.keys()):
    seq_hex = ' '.join(f'{ord(c):04X}' for c in seq)
    print(f"  {repr(seq)} ({seq_hex}) x{len(sequences[seq])}")
