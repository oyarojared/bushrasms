import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

p = Path(r"C:\Users\HP_User\Downloads\AAA Draft 2 (1).docx")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def para_text(para):
    parts = []
    for child in para.iter():
        tag = child.tag.split("}")[-1]
        if tag == "t" and child.text:
            parts.append(child.text)
        elif tag == "tab":
            parts.append("\t")
    return "".join(parts)

with zipfile.ZipFile(p) as z:
    root = ET.fromstring(z.read("word/document.xml"))

print("=== comment markers near Career Plans ===")
capture = False
for i, para in enumerate(root.iter(W + "p"), 1):
    t = para_text(para)
    ids = []
    for el in para.iter():
        tag = el.tag.split("}")[-1]
        if tag in {"commentRangeStart", "commentRangeEnd", "commentReference"}:
            ids.append(f"{tag}:{el.get(W + 'id')}")
    if "Career Plans" in t or "Objectives during" in t or "WHILE YOU ARE STUDYING" in t or "Moray House" in t or "five years" in t.lower() or "Long term" in t:
        capture = True
    if capture:
        if ids or "Moray" in t or "Career" in t or "Objectives" in t or "WHILE" in t or "five years" in t.lower():
            print(f"[{i}] ids={ids}")
            print(f"    {t[:220]!r}")
    if "Proposed Study in the UK" in t:
        break
