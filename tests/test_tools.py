from core.tools import FileReaderTool, OCRTool


def test_reads_text(fixtures_dir):
    result = FileReaderTool().forward(file_path=str(fixtures_dir / "sample.txt"))
    assert result["status"] == "success"
    assert "quick brown fox" in result["content"]


def test_truncates_long_text(fixtures_dir):
    result = FileReaderTool().forward(file_path=str(fixtures_dir / "multiline.txt"), max_lines=2)
    assert "truncated after 2 lines" in result["content"]


def test_summarizes_csv(fixtures_dir):
    result = FileReaderTool().forward(file_path=str(fixtures_dir / "test_data.csv"))
    analysis = result["content"]["analysis"]
    assert "3 rows" in analysis and "name, age, joined" in analysis


def test_reads_pdf_text(fixtures_dir):
    result = FileReaderTool().forward(file_path=str(fixtures_dir / "sample.pdf"))
    assert "Agents read PDF files too." in result["content"]


def test_missing_file_is_an_error_not_an_exception(tmp_path):
    result = FileReaderTool().forward(file_path=str(tmp_path / "nope.txt"))
    assert result["status"] == "error" and "File not found" in result["error"]


def test_ocr_rejects_missing_and_unsupported_files(tmp_path):
    assert OCRTool().forward(str(tmp_path / "missing.png")).startswith("Error: Image file not found")
    doc = tmp_path / "notes.txt"
    doc.write_text("hi")
    assert OCRTool().forward(str(doc)).startswith("Error: Unsupported image format")
