import pandas as pd


CATEGORIES = ["living costs", "food", "transportation", "hobbies"]

TARGETS: dict[str, float] = {
    "food": 300.0,
    "living costs": 100.0,
    "transportation": 30.0,
    "hobbies": 200.0,
}


def extract(image_bytes: bytes, mime_type: str, extractor_fn) -> dict:
    return extractor_fn(image_bytes, mime_type)


def append_entry(sheets_client, date, merchant, amount, currency, category) -> None:
    sheets_client.append_row([date, merchant, amount, currency, category], value_input_option="USER_ENTERED")


def compute_pivot(rows) -> pd.DataFrame:
    data: dict[str, dict[str, float]] = {}
    for row in rows:
        if isinstance(row, dict):
            date = row.get("Date") or row.get("date") or ""
            amount_raw = row.get("Amount") if row.get("Amount") is not None else row.get("amount")
            category = row.get("Category") or row.get("category") or ""
        else:
            if len(row) < 5:
                continue
            date, _, amount_raw, _, category = row[0], row[1], row[2], row[3], row[4]

        try:
            month = str(date)[:7]
            amount = float(amount_raw)
        except (TypeError, ValueError):
            continue

        if month not in data:
            data[month] = {cat: 0.0 for cat in CATEGORIES}
        if category in CATEGORIES:
            data[month][category] += amount

    df = pd.DataFrame.from_dict(data, orient="index", columns=CATEGORIES) if data else pd.DataFrame(columns=CATEGORIES)
    df = df.fillna(0).sort_index()
    df.index.name = "month"
    return df


def get_monthly_totals(df: pd.DataFrame, month: str) -> pd.Series:
    if month in df.index:
        return pd.Series(df.loc[month])
    return pd.Series(0.0, index=df.columns)


def get_rolling_average(df: pd.DataFrame, month: str, n: int = 3) -> pd.Series:
    prior = [m for m in df.index if m < month]
    prior = prior[-n:]
    if not prior:
        return pd.Series(0.0, index=df.columns)
    return pd.Series(df.loc[prior].mean())
