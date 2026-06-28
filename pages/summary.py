import os
import sys

import altair as alt
import gspread
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logic import CATEGORIES, TARGETS, compute_pivot, get_monthly_totals, get_rolling_average

load_dotenv()

st.set_page_config(page_title="Spending Summary")

st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        h1, h2, h3 { font-family: 'DM Mono', monospace !important; }
        [data-testid="stMetricLabel"] { font-family: 'DM Mono', monospace !important; }
        [data-testid="stMetricValue"] { font-family: 'DM Mono', monospace !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Spending Summary")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    sheet_id = st.secrets.get("GOOGLE_SHEET_ID") or os.environ["GOOGLE_SHEET_ID"]
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"], scope)
except Exception:
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"], scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(sheet_id).worksheet("expenses")
rows = sheet.get_all_records()

df = compute_pivot(rows)

if df.empty:
    st.info("No expenses recorded yet.")
    st.stop()

# Month selector
available_months = list(df.index)
current_month = pd.Timestamp.now().strftime("%Y-%m")
default_idx = available_months.index(current_month) if current_month in available_months else len(available_months) - 1
selected_month = st.selectbox("Month", available_months, index=default_idx)

monthly = get_monthly_totals(df, selected_month)
avg = get_rolling_average(df, selected_month)

# Metric cards
cols = st.columns(len(CATEGORIES))
for col, cat in zip(cols, CATEGORIES):
    spend = monthly[cat]
    delta = spend - avg[cat]
    col.metric(
        label=cat.title(),
        value=f"€{spend:,.0f}",
        delta=f"{delta:+,.0f}€ vs avg",
        delta_color="inverse",
    )

st.divider()

# Grouped bar chart: current month vs 3-month average
chart_data = pd.DataFrame(
    {
        "Category": [c.title() for c in CATEGORIES] * 2,
        "Amount": list(monthly[CATEGORIES]) + list(avg[CATEGORIES]),
        "Series": ["This Month"] * len(CATEGORIES) + ["3-Month Avg"] * len(CATEGORIES),
    }
)
grouped = (
    alt.Chart(chart_data)
    .mark_bar()
    .encode(
        x=alt.X("Category:N", axis=alt.Axis(labelAngle=0), title=None),
        xOffset="Series:N",
        y=alt.Y("Amount:Q", title="€"),
        color=alt.Color("Series:N", scale=alt.Scale(range=["#F59E0B", "#6B7280"])),
    )
    .properties(title="Current Month vs 3-Month Average", height=300)
)
st.altair_chart(grouped, use_container_width=True)

# Stacked area chart: all months
area_data = df[CATEGORIES].reset_index().melt(id_vars="month", var_name="category", value_name="amount")
area_data["category"] = area_data["category"].str.title()
area = (
    alt.Chart(area_data)
    .mark_area()
    .encode(
        x=alt.X("month:O", title="Month"),
        y=alt.Y("amount:Q", title="€", stack=True),
        color=alt.Color("category:N"),
    )
    .properties(title="Monthly Spend by Category", height=300)
)
st.altair_chart(area, use_container_width=True)

# Drill-down table
st.subheader("Transactions")

raw_records = []
for row in rows:
    if isinstance(row, dict):
        date = row.get("Date") or row.get("date") or ""
        merchant = row.get("Merchant") or row.get("merchant") or ""
        amount_raw = row.get("Amount") if row.get("Amount") is not None else row.get("amount")
        category = row.get("Category") or row.get("category") or ""
    else:
        if len(row) < 5:
            continue
        date, merchant, amount_raw, _, category = row[0], row[1], row[2], row[3], row[4]
    raw_records.append({"date": str(date), "merchant": merchant, "amount": amount_raw, "category": category})

raw_df = pd.DataFrame(raw_records, columns=["date", "merchant", "amount", "category"])
raw_df = raw_df[raw_df["date"].str.startswith(selected_month)]
raw_df = raw_df[raw_df["category"] != "investments"]

cat_options = ["All"] + [c.title() for c in CATEGORIES]
selected_cat = st.selectbox("Category filter", cat_options, key="cat_filter")
if selected_cat != "All":
    raw_df = raw_df[raw_df["category"].str.title() == selected_cat]

st.dataframe(raw_df[["date", "merchant", "amount"]].reset_index(drop=True), use_container_width=True)
st.caption(f"Months tracked: {len(df)}")
