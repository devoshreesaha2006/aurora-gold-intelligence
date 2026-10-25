"""Add encoding verification test to test_frontend_data_safety.py."""
import os

os.chdir(r"c:\Users\ASUS\OneDrive\Desktop\hacknHills\AURORA-website (1)\AURORA")

test_path = "backend/tests/test_frontend_data_safety.py"
with open(test_path, "r", encoding="utf-8") as f:
    content = f.read()

# Determine line ending
line_ending = "\r\n" if "\r\n" in content else "\n"

new_import_and_test = f"""from pathlib import Path{line_ending}import re{line_ending}{line_ending}{line_ending}ROOT = Path(__file__).resolve().parents[2]{line_ending}{line_ending}{line_ending}def test_opportunity_radar_encoding_is_clean_utf8():{line_ending}    \"\"\"Verify opportunity-radar.html has no mojibake / corrupted characters.\"\"\"{line_ending}    page = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8"){line_ending}{line_ending}    # Must contain correct Unicode special chars{line_ending}    assert "\\u20b9" in page, "Missing rupee sign U+20B9"{line_ending}    assert "\\u2014" in page, "Missing em-dash U+2014"{line_ending}    assert "\\u03c3" in page, "Missing sigma U+03C3"{line_ending}    assert "\\u2192" in page, "Missing right-arrow U+2192"{line_ending}    assert "\\u00b7" in page, "Missing middle-dot U+00B7"{line_ending}{line_ending}    # Must NOT contain box-drawing corruption artifacts{line_ending}    box_drawing = [c for c in set(page) if 0x2500 <= ord(c) <= 0x259F]{line_ending}    assert box_drawing == [], f"Box-drawing corruption remains: {{[f'U+{{ord(c):04X}}' for c in box_drawing]}}"{line_ending}{line_ending}    # Must NOT contain Greek Gamma (signature of CP1252 mojibake){line_ending}    assert "\\u0393" not in page, "Greek Gamma U+0393 mojibake remains"{line_ending}{line_ending}    # Title should read correctly{line_ending}    title_m = re.search(r"<title>(.*?)</title>", page){line_ending}    assert title_m, "No <title> tag found"{line_ending}    assert "\\u2014" in title_m.group(1) or "-" in title_m.group(1), "Title separator is corrupted"{line_ending}    assert "\\u0393" not in title_m.group(1), "Title contains mojibake Gamma"{line_ending}"""

# Replace the old header
old_header = f"from pathlib import Path{line_ending}{line_ending}{line_ending}ROOT = Path(__file__).resolve().parents[2]{line_ending}"

if old_header in content:
    content = content.replace(old_header, new_import_and_test, 1)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully added encoding test!")
else:
    print("ERROR: Could not find target header")
    # Debug
    first_200 = repr(content[:200])
    print(f"First 200 chars: {first_200}")
