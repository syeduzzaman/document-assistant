from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.config import Settings
from app.documents import DocumentError, chunk_pages, extract_pages, safe_filename


def make_pdf(page_texts):
    writer = PdfWriter()
    for text in page_texts:
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}),
        })
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 20 200 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_pdf_preserves_page_numbers():
    pages = extract_pages("policy.pdf", make_pdf(["Thirty days leave.", "Remote work is allowed."]), Settings())
    assert len(pages) == 2
    assert pages[0][0] == 1 and "Thirty days" in pages[0][1]
    assert pages[1][0] == 2 and "Remote work" in pages[1][1]
    chunks = chunk_pages(pages)
    assert [chunk.page for chunk in chunks] == [1, 2]


def test_chunk_overlap_and_provenance():
    text = " ".join(f"word{index}" for index in range(310))
    chunks = chunk_pages([(7, text)])
    assert [chunk.page for chunk in chunks] == [7, 7, 7]
    assert [chunk.index for chunk in chunks] == [0, 1, 2]
    assert chunks[0].text.split()[-25:] == chunks[1].text.split()[:25]
    assert chunks[-1].text.endswith("word309")


@pytest.mark.parametrize("name,data", [
    ("empty.txt", b""), ("bad.exe", b"binary"), ("bad.txt", bytes([0])),
    ("bad.txt", b"\xff"), ("bad.pdf", b"not a PDF"), ("broken.pdf", b"%PDF-broken"),
])
def test_invalid_documents_are_rejected(name, data):
    with pytest.raises(DocumentError):
        extract_pages(name, data, Settings())


def test_scanned_pdf_requires_ocr():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    output = BytesIO()
    writer.write(output)
    with pytest.raises(DocumentError, match="OCR"):
        extract_pages("scan.pdf", output.getvalue(), Settings())


def test_pdf_limits():
    with pytest.raises(DocumentError, match="40 pages"):
        extract_pages("pages.pdf", make_pdf(["page one", "page two"]), Settings(max_pages=1))


def test_text_limits_and_utf8():
    assert extract_pages("notes.md", "Grüße aus Düsseldorf".encode(), Settings())[0][1].startswith("Grüße")
    with pytest.raises(DocumentError, match="too large"):
        extract_pages("notes.txt", b"too much text", Settings(max_characters=3))


def test_filename_does_not_contain_path():
    assert safe_filename("../../secret.txt") == "secret.txt"
    assert safe_filename(r"C:\folder\policy.pdf") == "policy.pdf"
