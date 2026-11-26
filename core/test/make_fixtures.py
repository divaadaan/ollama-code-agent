"""Regenerate the fixture files the toolkit benchmark and the tests read: python core/test/make_fixtures.py"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent

SAMPLE_TEXT = "The quick brown fox jumps over the lazy dog.\n"
MULTILINE_TEXT = (
    "Agents plan before they act.\n\n"
    "They call tools to gather facts, read files and search the web.\n\n"
    "Then they check their work and give a final answer.\n"
)
CSV_TEXT = "name,age,joined\nAda,36,2021-03-01\nGrace,45,2019-07-15\nLinus,29,2023-01-09\n"
JSON_DATA = {"project": "ollama-api", "tools": [{"name": "file_reader", "local": True}], "version": 1}
IMAGE_TEXT = "HELLO AGENT 42"
PDF_TEXT = "Agents read PDF files too."


def write_pdf(path: Path, text: str) -> None:
    """A one-page PDF with one line of Helvetica text, built by hand so no PDF library is needed."""
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(out))


def write_image(path: Path, text: str) -> None:
    """Black text on white, large enough for Tesseract to read reliably."""
    image = Image.new("RGB", (900, 160), "white")
    font = ImageFont.load_default(size=72)
    ImageDraw.Draw(image).text((30, 40), text, fill="black", font=font)
    image.save(path)


def main() -> None:
    (HERE / "sample.txt").write_text(SAMPLE_TEXT, encoding="utf-8")
    (HERE / "multiline.txt").write_text(MULTILINE_TEXT, encoding="utf-8")
    (HERE / "test_data.csv").write_text(CSV_TEXT, encoding="utf-8")
    (HERE / "test_data.json").write_text(json.dumps(JSON_DATA, indent=2) + "\n", encoding="utf-8")
    write_image(HERE / "test_image.png", IMAGE_TEXT)
    write_pdf(HERE / "sample.pdf", PDF_TEXT)


if __name__ == "__main__":
    main()
