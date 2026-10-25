"""Scan all project files for mojibake / corrupted character sequences. Output via file."""
import os, sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

bad_patterns = [
    # Pattern bytes that appear when UTF-8 text was read as CP1252/Latin-1
    # Rupee sign U+20B9 = UTF-8 E2 82 B9 -> misread as â‚¹ or similar
    (b'\xe2\x82\xb9', 'Rupee sign raw UTF-8 bytes (check BOM/encoding declaration)'),
    # Em-dash U+2014 = UTF-8 E2 80 94 -> â€"
    (b'\xe2\x80\x94', 'Em-dash raw UTF-8'),
    # En-dash U+2013 = UTF-8 E2 80 93
    (b'\xe2\x80\x93', 'En-dash raw UTF-8'),
    # sigma U+03C3 = UTF-8 CF 83
    (b'\xcf\x83', 'Sigma raw UTF-8'),
    # mu U+03BC = UTF-8 CE BC
    (b'\xce\xbc', 'Mu raw UTF-8'),
    # bullet U+2022 = UTF-8 E2 80 A2
    (b'\xe2\x80\xa2', 'Bullet raw UTF-8'),
    # These are the actual mojibake strings (UTF-8 decoded as Latin-1 then re-encoded)
    # We search for these as text strings in the file
]

# Also search for these text patterns (the actual mojibake as unicode strings)
text_patterns = [
    ('\u00e2\u0082\u00b9', 'Mojibake rupee (UTF-8 bytes read as Latin-1): â‚¹'),
    ('\u00e2\u0080\u0094', 'Mojibake em-dash (UTF-8 bytes read as Latin-1): â€"'),
    ('\u00e2\u0080\u0093', 'Mojibake en-dash: â€"'),
    ('\u00cf\u0083', 'Mojibake sigma: Ïƒ'),
    ('\u00ce\u00bc', 'Mojibake mu: Î¼'),
    # Windows-1252 corruption patterns (ΓÇ etc.) - these happen when CP1252 bytes are read as UTF-8 incorrectly
    ('\u0393\u00c7', 'Windows Gamma-C pattern (CP1252 misread)'),
    ('\u2560\u255e', 'Box-drawing chars (encoding confusion)'),
]

files_to_check = []
for root, dirs, files in os.walk('.'):
    for skip in ['.venv', '.git', '__pycache__', 'node_modules', 'opportunity-radar-original-backup.html']:
        if skip in dirs:
            dirs.remove(skip)
    for fn in files:
        if fn.endswith(('.html', '.js', '.css', '.py')):
            files_to_check.append(os.path.join(root, fn))

results = []

for fpath in files_to_check:
    if 'opportunity-radar-original-backup' in fpath:
        continue
    try:
        with open(fpath, 'rb') as f:
            raw = f.read()
        # Check BOM
        has_bom = raw.startswith(b'\xef\xbb\xbf')

        # Check for raw non-UTF-8 bytes in files that should be UTF-8
        text_utf8 = raw.lstrip(b'\xef\xbb\xbf').decode('utf-8', errors='replace')
        text_latin1 = raw.decode('latin-1')

        file_hits = []
        if has_bom:
            file_hits.append(('BOM', 'File has UTF-8 BOM (\xef\xbb\xbf) - may cause browser issues', 1, ''))

        for pattern_str, desc in text_patterns:
            if pattern_str in text_latin1:
                for i, line in enumerate(text_latin1.splitlines(), 1):
                    if pattern_str in line:
                        file_hits.append((pattern_str[:6], desc, i, line.strip()[:100]))

        # Also check for replacement char (U+FFFD) which indicates bad UTF-8 decode
        if '\ufffd' in text_utf8:
            for i, line in enumerate(text_utf8.splitlines(), 1):
                if '\ufffd' in line:
                    file_hits.append(('FFFD', 'Invalid UTF-8 sequence -> replacement char', i, line.strip()[:100]))
                    break

        if file_hits:
            results.append((fpath, file_hits))

    except Exception as e:
        results.append((fpath, [('ERR', str(e), 0, '')]))

output_path = 'audit_encoding_results.txt'
with open(output_path, 'w', encoding='utf-8') as out:
    if results:
        out.write(f"ENCODING ISSUES FOUND IN {len(results)} FILES:\n\n")
        for fp, hits in sorted(results):
            out.write(f"=== {fp} ===\n")
            seen = set()
            for pattern, desc, lineno, snippet in hits[:8]:
                key = (desc[:30], lineno)
                if key not in seen:
                    seen.add(key)
                    out.write(f"  Line {lineno}: [{desc}]\n")
                    if snippet:
                        out.write(f"    {snippet}\n")
    else:
        out.write("NO ENCODING ISSUES FOUND.\n")

print(f"Done. Results written to {output_path}")
print(f"Files scanned: {len(files_to_check)}")
print(f"Files with issues: {len(results)}")
