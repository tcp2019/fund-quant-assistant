from pathlib import Path

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
