"""Verify exactly what characters are in key spots of the live active files."""
import os, re

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

files_to_check = {
    'opportunity-radar.html': [b'<title>', b'ticker-price', b'benchmark_basis', b'matrix'],
    'aurora-pipeline.js': [b'rupee', b'Norm Price', b'benchmark'],
    'dashboard.html': [b'<title>', b'995 Fine Gold'],
    'market-detective.html': [b'<title>'],
    'backtesting-lab.html': [b'<title>'],
    'contract-explorer.html': [b'<title>'],
}

CORRECT_RUPEE = b'\xe2\x82\xb9'   # U+20B9 ₹ in UTF-8
CORRECT_EMDASH = b'\xe2\x80\x94'  # U+2014 — in UTF-8
CORRECT_ENDASH = b'\xe2\x80\x93'  # U+2013 – in UTF-8
CORRECT_SIGMA = b'\xcf\x83'       # U+03C3 σ in UTF-8
CORRECT_MU = b'\xce\xbc'          # U+03BC μ in UTF-8

with open('enc_verify.txt', 'w', encoding='utf-8') as out:
    for fname in files_to_check:
        if not os.path.exists(fname):
            out.write(f"\n=== {fname} NOT FOUND ===\n")
            continue
        with open(fname, 'rb') as f:
            raw = f.read()
        
        out.write(f"\n=== {fname} ===\n")
        out.write(f"  File size: {len(raw)} bytes\n")
        out.write(f"  BOM present: {raw[:3] == b'\xef\xbb\xbf'}\n")
        out.write(f"  Correct rupee (U+20B9) count: {raw.count(CORRECT_RUPEE)}\n")
        out.write(f"  Correct em-dash (U+2014) count: {raw.count(CORRECT_EMDASH)}\n")
        out.write(f"  Correct en-dash (U+2013) count: {raw.count(CORRECT_ENDASH)}\n")
        out.write(f"  Correct sigma (U+03C3) count: {raw.count(CORRECT_SIGMA)}\n")
        out.write(f"  Correct mu (U+03BC) count: {raw.count(CORRECT_MU)}\n")
        
        # Extract title
        title_m = re.search(rb'<title>(.*?)</title>', raw, re.DOTALL)
        if title_m:
            t = title_m.group(1)
            out.write(f"  Title bytes hex: {t.hex()}\n")
            out.write(f"  Title as UTF-8: {t.decode('utf-8', errors='replace')}\n")
        
        # Check for any non-ASCII bytes that are NOT part of valid UTF-8 rupee, em-dash, en-dash, sigma, mu
        # by decoding as UTF-8 and looking for replacement chars
        decoded = raw.decode('utf-8', errors='replace')
        repl_count = decoded.count('\ufffd')
        if repl_count:
            out.write(f"  INVALID UTF-8 sequences: {repl_count} replacement chars\n")
        else:
            out.write(f"  UTF-8 validity: CLEAN\n")
        
        # Check specific non-ASCII chars present
        non_ascii_chars = {}
        for cp in set(ord(c) for c in decoded if ord(c) > 127):
            char = chr(cp)
            count = decoded.count(char)
            name = ''
            if cp == 0x20B9: name = 'RUPEE SIGN ₹'
            elif cp == 0x2014: name = 'EM DASH —'
            elif cp == 0x2013: name = 'EN DASH –'
            elif cp == 0x03C3: name = 'SIGMA σ'
            elif cp == 0x03BC: name = 'MU μ'
            elif cp == 0x2022: name = 'BULLET •'
            elif cp == 0x00B7: name = 'MIDDLE DOT ·'
            elif cp == 0x00D7: name = 'MULTIPLICATION ×'
            elif cp == 0x0393: name = 'GREEK GAMMA Γ - POSSIBLE CORRUPTION'
            elif cp == 0x00C7: name = 'C WITH CEDILLA Ç - POSSIBLE CORRUPTION'
            elif cp == 0x00F6: name = 'O WITH UMLAUT ö - POSSIBLE CORRUPTION'
            elif cp == 0x0399: name = 'GREEK IOTA Ι - POSSIBLE CORRUPTION'
            elif cp == 0x0391: name = 'GREEK ALPHA Α - POSSIBLE CORRUPTION'
            non_ascii_chars[cp] = (char, count, name)
        
        suspicious = [(cp, char, count, name) for cp, (char, count, name) in non_ascii_chars.items() 
                      if 'CORRUPTION' in name]
        if suspicious:
            out.write(f"  SUSPICIOUS CHARS:\n")
            for cp, char, count, name in sorted(suspicious):
                out.write(f"    U+{cp:04X} {char!r} x{count}: {name}\n")
                # Find context
                for i, line in enumerate(decoded.splitlines(), 1):
                    if char in line:
                        out.write(f"      Line {i}: {line.strip()[:120]}\n")
                        break

print("Done - results in enc_verify.txt")
