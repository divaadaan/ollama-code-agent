# Fixtures

Inputs for the toolkit benchmark (`GET /toolkit-test`) and the tests. `python core/test/make_fixtures.py`
regenerates all of them.

| File | Used by |
|---|---|
| `sample.txt`, `multiline.txt` | `file_reader` (text, truncation) |
| `test_data.csv` | `file_reader` (CSV summary) |
| `test_data.json` | `file_reader` (JSON) |
| `sample.pdf` | `file_reader` (PDF text), built by hand with no PDF library |
| `test_image.png` | `extract_text_ocr`, `image_to_text` |

There is no audio fixture yet, so `speech_to_text` has no benchmark case, and no Excel fixture (reading `.xlsx`
needs `openpyxl`, which is not a dependency).
