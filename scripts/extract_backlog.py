"""Convert the supplied backlog's paragraphs and tables without third-party packages."""

from collections import Counter
from hashlib import sha256
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Backlog_DocGen_DocTemplating_DocDigitization.docx"
TARGET = ROOT / "docs" / "epics.md"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def text(node):
    return "".join(part.text or "" for part in node.findall(".//w:t", NS))


def convert():
    with ZipFile(SOURCE) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find("w:body", NS)
    stories = []
    output = [
        "# Product backlog: all epics and stories",
        "",
        f"Source: [{SOURCE.name}](../{SOURCE.name}). Extracted on 2026-09-22.",
        f"Source SHA-256: `{sha256(SOURCE.read_bytes()).hexdigest()}`.",
        "",
        "This is a faithful text/table transcription. Story IDs, acceptance criteria, priorities, sizes and releases are preserved. This transcription does not claim delivery; see [E1 implementation status](e1-foundation.md) for current progress. Regenerate with `python scripts/extract_backlog.py`; put analysis and scope changes in the other planning documents, not in this generated file.",
        "",
        "See [stack proposal](tech-stack.md), [delivery analysis](implementation-plan.md), and [decision log](design-decisions.md).",
        "",
    ]
    headings = {
        "Product backlog", "Conventions and epic index",
        "Release summary, MVP sequencing and quality bar",
        "Suggested internal MVP milestones", "Quality bar for every release",
        "Definition of done for a story",
    }
    for node in body:
        kind = node.tag.rsplit("}", 1)[-1]
        if kind == "p":
            value = text(node)
            if value:
                prefix = "## " if value in headings or re.match(r"^E\d+ ", value) else ""
                output.extend([prefix + value, ""])
        elif kind == "tbl":
            rows = [[text(cell) for cell in row.findall("w:tc", NS)]
                    for row in node.findall("w:tr", NS)]
            for row in rows:
                if row and re.fullmatch(r"E\d+-\d+", row[0]):
                    if len(row) != 6:
                        raise ValueError(f"Unexpected story shape: {row}")
                    stories.append(row)
            for index, row in enumerate(rows):
                output.append("| " + " | ".join(cell.replace("|", "&#124;").replace("\n", "<br>") for cell in row) + " |")
                if index == 0:
                    output.append("| " + " | ".join("---" for _ in row) + " |")
            output.append("")
    ids = [row[0] for row in stories]
    assert len(ids) == len(set(ids)) == 218, "Unexpected/missing/duplicate source stories"
    counts = Counter(row[5] for row in stories)
    assert counts == {"MVP": 91, "R2": 67, "R3": 30, "R4": 30}, counts
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text("\n".join(output), encoding="utf-8")
    print(f"Preserved {len(stories)} unique stories across {len({i.split('-')[0] for i in ids})} epics: {dict(counts)}")


if __name__ == "__main__":
    convert()
