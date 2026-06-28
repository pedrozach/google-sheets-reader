import io
from unittest.mock import MagicMock

import pytest

from app import create_app


FIXTURE_EXTRACTION = {
    "place": "Lidl",
    "value": 28.47,
    "currency": "EUR",
    "date": "2026-05-21",
    "category": "food",
}

FIXTURE_ROWS = [
    ["2026-05-21", "Lidl", "28.47", "EUR", "food"],
    ["2026-05-10", "Uber", "12.00", "EUR", "transportation"],
    ["2026-06-03", "Lidl", "35.00", "EUR", "food"],
]


@pytest.fixture
def upload_client():
    def fake_extractor(image_bytes, mime_type):
        return FIXTURE_EXTRACTION.copy()

    app = create_app(extractor=fake_extractor, sheets_client=MagicMock())
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def failing_upload_client():
    def fake_extractor(image_bytes, mime_type):
        raise ValueError("GPT-4o unavailable")

    app = create_app(extractor=fake_extractor, sheets_client=MagicMock())
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def confirm_client():
    fake_sheet = MagicMock()
    app = create_app(extractor=MagicMock(), sheets_client=fake_sheet)
    app.config["TESTING"] = True
    return app.test_client(), fake_sheet


@pytest.fixture
def summary_client():
    fake_sheet = MagicMock()
    fake_sheet.get_all_values.return_value = FIXTURE_ROWS
    app = create_app(extractor=MagicMock(), sheets_client=fake_sheet)
    app.config["TESTING"] = True
    return app.test_client()


def _fake_image():
    return (io.BytesIO(b"fakeimagebytes"), "invoice.jpg")


def test_upload_happy_path(upload_client):
    data = {"invoice": _fake_image()}
    resp = upload_client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Lidl" in body
    assert "28.47" in body
    assert "EUR" in body
    assert "2026-05-21" in body
    assert "food" in body


def test_upload_extraction_failure_returns_friendly_error(failing_upload_client):
    data = {"invoice": _fake_image()}
    resp = failing_upload_client.post(
        "/upload", data=data, content_type="multipart/form-data", follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"500" not in resp.data
    body = resp.data.decode()
    assert "Extraction failed" in body or "error" in body.lower()


def test_confirm_appends_correct_row(confirm_client):
    client, fake_sheet = confirm_client
    form = {
        "date": "2026-05-21",
        "merchant": "Lidl",
        "amount": "28.47",
        "currency": "EUR",
        "category": "food",
    }
    resp = client.post("/confirm", data=form, follow_redirects=False)
    assert resp.status_code in (301, 302)
    fake_sheet.append_row.assert_called_once_with(
        ["2026-05-21", "Lidl", "28.47", "EUR", "food"]
    )


def test_summary_shows_aggregated_totals(summary_client):
    resp = summary_client.get("/summary")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "2026-05" in body
    assert "2026-06" in body
    # May total: food 28.47 + transportation 12.00
    assert "28.47" in body or "40.47" in body
    assert "12.00" in body
    # June total: food 35.00
    assert "35.00" in body
