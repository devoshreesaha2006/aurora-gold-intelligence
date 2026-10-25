"""Fix encoding corruption in opportunity-radar.html - no stdout output of non-ASCII."""
import os, re, sys

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

with open('opportunity-radar.html', 'r', encoding='utf-8') as f:
    content = f.read()

original_length = len(content)

# Full replacement map (ordered longest-first to avoid partial replacements)
replacements = [
    ('\u0393\u00e9\u2563', '\u20b9'),   # Rupee sign Rs
    ('\u0393\u00c7\u00f6', '\u2014'),   # Em-dash
    ('\u0393\u00c7\u00f4', '\u2013'),   # En-dash
    ('\u0393\u00c7\u00aa', '\u2026'),   # Ellipsis
    ('\u0393\u00e5\u00c6', '\u2192'),   # Right arrow
    ('\u0393\u00eb\u00d1', '\u2265'),   # Greater-than-or-equal
    ('\u2566\u2557', '\u00b7'),          # Box drawing -> middle dot
    ('\u252c\u2557', '\u00b7'),          # Box drawing -> middle dot
    ('\u2567\u00e2', '\u03c3'),          # sigma
]

log_lines = [f"Original length: {original_length}"]

applied_count = 0
for old, new in replacements:
    count = content.count(old)
    if count > 0:
        content = content.replace(old, new)
        applied_count += 1
        log_lines.append(f"  Replaced U+{ord(old[0]):04X}... -> U+{ord(new):04X}: {count} times")

log_lines.append(f"After replacements length: {len(content)}")

# Verify remaining suspicious chars
suspicious_chars = {
    0x0393: 'GREEK GAMMA',
    0x2567: 'BOX T-UP',
    0x2566: 'BOX DOWN',
    0x252c: 'BOX DOWN-HRZ',
    0x2563: 'BOX DBL-VERT',
}

remaining = {}
for cp, name in suspicious_chars.items():
    char = chr(cp)
    count = content.count(char)
    if count > 0:
        remaining[cp] = (char, count, name)
        for i, line in enumerate(content.splitlines(), 1):
            if char in line:
                remaining[cp] = (char, count, name, i, line.strip()[:80])
                break

if remaining:
    log_lines.append("REMAINING SUSPICIOUS CHARS:")
    for cp, info in sorted(remaining.items()):
        log_lines.append(f"  U+{cp:04X} {info[2]} x{info[1]}")
        if len(info) > 3:
            log_lines.append(f"    Line {info[3]}: {info[4]}")
else:
    log_lines.append("All suspicious chars resolved!")

# Verification counts
log_lines.append("VERIFICATION:")
log_lines.append(f"  Rupee U+20B9 count: {content.count(chr(0x20B9))}")
log_lines.append(f"  Em-dash U+2014 count: {content.count(chr(0x2014))}")
log_lines.append(f"  En-dash U+2013 count: {content.count(chr(0x2013))}")
log_lines.append(f"  Sigma U+03C3 count: {content.count(chr(0x03C3))}")
log_lines.append(f"  Arrow U+2192 count: {content.count(chr(0x2192))}")
log_lines.append(f"  Ellipsis U+2026 count: {content.count(chr(0x2026))}")
log_lines.append(f"  Middle-dot U+00B7 count: {content.count(chr(0x00B7))}")

# Write fixed file
with open('opportunity-radar.html', 'w', encoding='utf-8') as f:
    f.write(content)

log_lines.append("File written successfully!")

with open('fix_encoding_log.txt', 'w', encoding='utf-8') as logf:
    for line in log_lines:
        logf.write(line + '\n')

print("Done - see fix_encoding_log.txt")
print(f"Applied {applied_count} replacement types")
