import threading

from app.services.ocr.pipeline import extract_text_from_ocr_result


def test_extract_text_from_paddleocr_v3_result():
    result = [{"rec_texts": ["易方达优质精选混合", "110011", "持有份额 1000.00"]}]
    text = extract_text_from_ocr_result(result)
    assert "110011" in text
    assert "1000.00" in text


def test_extract_text_from_legacy_result():
    box = [[0, 0], [1, 0], [1, 1], [0, 1]]
    result = [[[box, ("hello", 0.99)]]]
    text = extract_text_from_ocr_result(result)
    assert text == "hello"


def test_paddle_engine_init_is_thread_safe(monkeypatch):
    import app.services.ocr.pipeline as pipeline

    monkeypatch.setattr(pipeline, "_ocr_engine", None)
    init_count = 0
    lock = threading.Lock()

    class FakeOCR:
        def ocr(self, image_path):
            return [{"rec_texts": [f"ok:{image_path}"]}]

    def fake_create():
        nonlocal init_count
        with lock:
            init_count += 1
        return FakeOCR()

    monkeypatch.setattr(pipeline, "_create_paddle_ocr_engine", fake_create)

    barrier = threading.Barrier(4)

    def worker(path: str) -> str:
        barrier.wait()
        return pipeline.run_paddle_ocr(path)

    threads = [
        threading.Thread(target=worker, args=(f"/tmp/{i}.png",))
        for i in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert init_count == 1
