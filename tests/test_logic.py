import pytest
import pandas as pd

from logic import compute_pivot, append_entry, extract, get_monthly_totals, get_rolling_average, CATEGORIES


# ---------------------------------------------------------------------------
# 1. compute_pivot happy path
# ---------------------------------------------------------------------------

def test_compute_pivot_happy_path():
    rows = [
        {"date": "2024-01-15", "merchant": "Supermarket", "amount": "120.50", "currency": "USD", "category": "food"},
        {"date": "2024-01-20", "merchant": "Bus", "amount": "30.00", "currency": "USD", "category": "transportation"},
        {"date": "2024-02-05", "merchant": "Rent", "amount": "900.00", "currency": "USD", "category": "living costs"},
        {"date": "2024-02-10", "merchant": "Cinema", "amount": "25.00", "currency": "USD", "category": "hobbies"},
        # investments row — must be silently excluded
        {"date": "2024-02-15", "merchant": "Stocks", "amount": "500.00", "currency": "USD", "category": "investments"},
    ]

    df = compute_pivot(rows)

    assert list(df.index) == ["2024-01", "2024-02"]
    assert df.index.name == "month"

    assert list(df.columns) == CATEGORIES
    assert "investments" not in df.columns

    assert df.loc["2024-01", "food"] == pytest.approx(120.50)
    assert df.loc["2024-01", "transportation"] == pytest.approx(30.00)
    assert df.loc["2024-02", "living costs"] == pytest.approx(900.00)
    assert df.loc["2024-02", "hobbies"] == pytest.approx(25.00)
    # investments row did not create a column or inflate any total
    assert df.loc["2024-02"].sum() == pytest.approx(925.00)


# ---------------------------------------------------------------------------
# 2. compute_pivot malformed rows — silently skipped
# ---------------------------------------------------------------------------

def test_compute_pivot_malformed_rows():
    rows = [
        {"date": "2024-03-01", "merchant": "A", "amount": "", "currency": "USD", "category": "food"},
        {"date": "2024-03-02", "merchant": "B", "amount": None, "currency": "USD", "category": "food"},
        {"date": "2024-03-03", "merchant": "C", "amount": "abc", "currency": "USD", "category": "food"},
        # One valid row so the DataFrame is not empty
        {"date": "2024-03-10", "merchant": "D", "amount": "50.00", "currency": "USD", "category": "food"},
    ]

    df = compute_pivot(rows)

    assert df.loc["2024-03", "food"] == pytest.approx(50.00)
    assert list(df.index) == ["2024-03"]


# ---------------------------------------------------------------------------
# 3. append_entry — fake Sheets client
# ---------------------------------------------------------------------------

class FakeSheetsClient:
    def __init__(self):
        self.calls = []

    def append_row(self, row, **kwargs):
        self.calls.append(row)


def test_append_entry_calls_append_row_once():
    client = FakeSheetsClient()
    date = "2024-04-01"
    merchant = "Coffee Shop"
    amount = 4.50
    currency = "USD"
    category = "food"

    append_entry(client, date, merchant, amount, currency, category)

    assert len(client.calls) == 1
    assert client.calls[0] == [date, merchant, amount, currency, category]


# ---------------------------------------------------------------------------
# 4. extract happy path — fake extractor callable
# ---------------------------------------------------------------------------

FIXTURE_RESULT = {
    "date": "2024-05-01",
    "merchant": "Restaurant",
    "amount": 42.00,
    "currency": "EUR",
    "category": "food",
}


def fake_extractor_ok(image_bytes, mime_type):
    return FIXTURE_RESULT


def test_extract_happy_path():
    result = extract(b"fake-image-bytes", "image/jpeg", fake_extractor_ok)

    assert result == FIXTURE_RESULT
    assert set(result.keys()) == {"date", "merchant", "amount", "currency", "category"}
    assert result["date"] == "2024-05-01"
    assert result["merchant"] == "Restaurant"
    assert result["amount"] == 42.00
    assert result["currency"] == "EUR"
    assert result["category"] == "food"


# ---------------------------------------------------------------------------
# 5. extract failure — fake extractor that raises RuntimeError
# ---------------------------------------------------------------------------

def fake_extractor_fail(image_bytes, mime_type):
    raise RuntimeError("extraction failed")


def test_extract_propagates_runtime_error():
    with pytest.raises(RuntimeError, match="extraction failed"):
        extract(b"fake-image-bytes", "image/png", fake_extractor_fail)


# ---------------------------------------------------------------------------
# Helpers shared by get_monthly_totals / get_rolling_average tests
# ---------------------------------------------------------------------------

def _make_pivot():
    rows = [
        {"date": "2024-01-10", "merchant": "A", "amount": "100", "currency": "EUR", "category": "food"},
        {"date": "2024-01-10", "merchant": "B", "amount": "20",  "currency": "EUR", "category": "transportation"},
        {"date": "2024-02-10", "merchant": "C", "amount": "200", "currency": "EUR", "category": "food"},
        {"date": "2024-02-10", "merchant": "D", "amount": "40",  "currency": "EUR", "category": "hobbies"},
        {"date": "2024-03-10", "merchant": "E", "amount": "150", "currency": "EUR", "category": "food"},
        {"date": "2024-03-10", "merchant": "F", "amount": "60",  "currency": "EUR", "category": "living costs"},
        {"date": "2024-04-10", "merchant": "G", "amount": "300", "currency": "EUR", "category": "food"},
    ]
    return compute_pivot(rows)


# ---------------------------------------------------------------------------
# 6. get_monthly_totals
# ---------------------------------------------------------------------------

def test_get_monthly_totals_known_month():
    df = _make_pivot()
    totals = get_monthly_totals(df, "2024-02")
    assert totals["food"] == pytest.approx(200.0)
    assert totals["hobbies"] == pytest.approx(40.0)
    assert totals["transportation"] == pytest.approx(0.0)


def test_get_monthly_totals_missing_month():
    df = _make_pivot()
    totals = get_monthly_totals(df, "2099-01")
    assert list(totals.index) == CATEGORIES
    assert (totals == 0.0).all()


# ---------------------------------------------------------------------------
# 7. get_rolling_average
# ---------------------------------------------------------------------------

def test_get_rolling_average_full_window():
    df = _make_pivot()
    # prior 3 months before 2024-04 are 2024-01, 2024-02, 2024-03
    avg = get_rolling_average(df, "2024-04", n=3)
    expected_food = (100 + 200 + 150) / 3
    assert avg["food"] == pytest.approx(expected_food)


def test_get_rolling_average_partial_window():
    df = _make_pivot()
    # only 2024-01 exists before 2024-02
    avg = get_rolling_average(df, "2024-02", n=3)
    assert avg["food"] == pytest.approx(100.0)
    assert avg["transportation"] == pytest.approx(20.0)


def test_get_rolling_average_excludes_target_month():
    df = _make_pivot()
    # 2024-04 itself must not be included in its own average
    avg = get_rolling_average(df, "2024-04", n=3)
    assert avg["food"] != pytest.approx(300.0)


def test_get_rolling_average_no_prior_data():
    df = _make_pivot()
    avg = get_rolling_average(df, "2024-01")
    assert list(avg.index) == CATEGORIES
    assert (avg == 0.0).all()
