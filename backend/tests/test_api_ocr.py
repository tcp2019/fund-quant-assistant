from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FIXTURES = Path(__file__).parent / "fixtures" / "ocr"


def test_ocr_upload_and_confirm():
    alipay_text = (FIXTURES / "alipay_sample.txt").read_text(encoding="utf-8")
    upload = client.post("/api/ocr/upload", json={"platform": "alipay", "text": alipay_text})
    assert upload.status_code == 200
    job_id = upload.json()["job_id"]
    assert len(upload.json()["holdings"]) == 1
    confirm = client.post(f"/api/ocr/{job_id}/confirm", json={"holdings": upload.json()["holdings"]})
    assert confirm.status_code == 201
    overview = client.get("/api/portfolio/overview").json()
    assert overview["total_value"] == 1800


def test_ocr_upload_file_with_mocked_paddle():
    alipay_text = (FIXTURES / "alipay_sample.txt").read_text(encoding="utf-8")
    with patch("app.api.routes.ocr.run_paddle_ocr", return_value=alipay_text):
        response = client.post(
            "/api/ocr/upload",
            files={"file": ("screenshot.png", b"fake-image-bytes", "image/png")},
            data={"platform": "alipay"},
        )
    assert response.status_code == 200
    assert len(response.json()["holdings"]) == 1


def test_ocr_upload_file_without_paddle():
    with patch(
        "app.api.routes.ocr.run_paddle_ocr",
        side_effect=ImportError(
            "PaddleOCR is not installed. Use text upload mode or install OCR extras: "
            "pip install 'fund-quant-assistant[ocr]'"
        ),
    ):
        response = client.post(
            "/api/ocr/upload",
            files={"file": ("screenshot.png", b"fake-image-bytes", "image/png")},
        )
    assert response.status_code == 501
    assert "text upload mode" in response.json()["detail"]
