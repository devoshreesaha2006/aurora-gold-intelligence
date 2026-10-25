"""Deep investigation of the encoding corruption."""
import re, sys, os

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

with open('opportunity-radar.html', 'rb') as f:
    raw = f.read()

title_m = re.search(rb'<title>(.*?)</title>', raw, re.DOTALL)
if title_m:
    title_raw = title_m.group(1)
    title_hex = title_raw.hex()
    title_utf8 = title_raw.decode('utf-8', errors='replace')
    title_latin1 = title_raw.decode('latin-1')

with open('enc_investigation.txt', 'w', encoding='utf-8') as out:
    out.write(f"Title hex: {title_hex}\n")
    out.write(f"Title as UTF-8: {title_utf8}\n")
    out.write(f"Title as latin-1: {title_latin1}\n")
    
    # The title hex is: 4155524f524120 ce93 c387 c3b6 20 4f7070...
    # ce93 = UTF-8 for U+0393 = Γ (Greek Capital Gamma)
    # c387 = UTF-8 for U+00C7 = Ç (C with cedilla)
    # c3b6 = UTF-8 for U+00F6 = ö (o with umlaut)
    # So the title is "AURORA Γö Opportunity Radar"
    # This was supposed to be "AURORA — Opportunity Radar" (em-dash)
    # 
    # Em-dash U+2014 in UTF-8 = E2 80 94
    # How did E2 80 94 become CE 93 C3 87 C3 B6?
    # 
    # Hypothesis: double-encoding where UTF-8 bytes were interpreted as latin-1 then re-encoded as UTF-8
    # E2 -> 0xE2 as latin-1 -> â -> UTF-8: C3 A2
    # 80 -> 0x80 as CP1252 = € -> UTF-8: E2 82 AC
    # 94 -> 0x94 as CP1252 = " (right double quote) -> UTF-8: E2 80 9D
    # That doesn't match either.
    #
    # Actually ce93 = Γ, c3 87 = Ç, c3 b6 = ö
    # What if we decode these UTF-8 codepoints back to bytes?
    # U+0393 = 0xCE, 0x93 -- already IS the bytes  
    # Let's try: what does "Γö" look like in various encodings?
    
    # Actually: look at what specific bytes we have: CE 93 C3 87 C3 B6
    # If we take just the low bytes: 0x93, 0x87, 0xB6 -- in CP1252:
    # 0x93 = left double quotation mark "
    # 0x87 = dagger
    # 0xB6 = pilcrow ¶
    # That doesn't give em-dash
    
    # Alternative: the file was originally Windows-1252 and contained:
    # \x97 (Windows em-dash) - but that's ONE byte not three
    
    # Let me try: if the original had UTF-8 em-dash (E2 80 94) but was saved 
    # as CP1252, then each byte E2, 80, 94 would be:
    # E2 = Γ in cp1252? No, E2 = â
    # Actually wait. What if the bytes CE 93 represent the UTF-8 
    # encoding of something that was double-encoded?
    # 
    # U+0393 Γ was obtained by: original byte 0xCE + 0x93
    # If a file had windows-1252 bytes and those bytes were:
    # 0xCE = Î in latin-1 (no CP1252 mapping)  
    # 0x93 = " (left curly quote) in CP1252
    # Combined would read as "Î"" = mojibake
    # 
    # Most likely the em-dash symbol character was pasted differently
    # Let's just check: "—" em-dash is U+2014
    # In the actual aurora-pipeline.js we see: â€" which IS the mojibake for U+2014
    # encoded as Latin-1 reading of UTF-8 bytes
    
    out.write("\nKey insight: Files ARE UTF-8 but CONTAIN the mojibake STRINGS literally\n")
    out.write("The issue: The source code itself has the mojibake strings HARDCODED\n")
    out.write("(Not a runtime encoding issue, but the actual characters in the file are wrong)\n\n")
    
    # Let's verify by looking at aurora-pipeline.js rupee occurrences
    with open('aurora-pipeline.js', 'rb') as f:
        pipeline_raw = f.read()
    
    # Search for rupee pattern in pipeline
    # Correct rupee: E2 82 B9 (UTF-8 for U+20B9)
    correct_rupee_count = pipeline_raw.count(b'\xe2\x82\xb9')
    # Mojibake rupee: C3 A2 E2 80 9A C2 B9 (UTF-8 encoding of the mojibake "â‚¹")
    # The mojibake string â‚¹ is: U+00E2 U+20AC U+00B9 but wait...
    # Actually â = U+00E2, ‚ = U+201A, ¹ = U+00B9
    # In UTF-8: C3 A2, E2 80 9A, C2 B9
    
    # Let's find where "rupee-like" bytes appear
    # The audit script found "â‚¹" pattern. Let me check what bytes that is in UTF-8
    mojibake_str = '\u00e2\u0082\u00b9'  # These are the UNICODE codepoints of the mojibake
    mojibake_bytes_utf8 = mojibake_str.encode('utf-8')
    out.write(f"Mojibake rupee as unicode codepoints: {[hex(ord(c)) for c in mojibake_str]}\n")
    out.write(f"Mojibake rupee encoded as UTF-8: {mojibake_bytes_utf8.hex()}\n")
    
    mojibake_count = pipeline_raw.count(mojibake_bytes_utf8)
    out.write(f"Correct rupee (E2 82 B9) count in aurora-pipeline.js: {correct_rupee_count}\n")
    out.write(f"Mojibake rupee in aurora-pipeline.js: {mojibake_count}\n")
    
    # Find the actual bytes near a known "rupee" location
    # Line 521 of aurora-pipeline.js: "<th>Norm Price (â¹/g Fine)</th>"
    # Find that string as bytes
    search = b'Norm Price'
    idx = pipeline_raw.find(search)
    if idx >= 0:
        snippet = pipeline_raw[idx:idx+40]
        out.write(f"\nSnippet near 'Norm Price' in pipeline: {snippet.hex()}\n")
        out.write(f"Decoded as UTF-8: {snippet.decode('utf-8', errors='replace')}\n")
        out.write(f"Decoded as latin-1: {snippet.decode('latin-1')}\n")

print("Investigation written to enc_investigation.txt")
