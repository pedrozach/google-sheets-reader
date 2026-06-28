import os
import datetime
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logic

load_dotenv()

SARCASM = {
    "food": [
        "Another meal out? Shocking.",
        "Cooking at home not an option, I see.",
        "Your kitchen misses you.",
        "Bold choice. Eating again.",
    ],
    "living costs": [
        "Ah yes, existing. Very expensive habit.",
        "The audacity of having a roof over your head.",
        "Survival costs money. Who knew.",
        "Basic needs? How extravagant.",
    ],
    "transportation": [
        "Going places? Must be nice.",
        "Can't walk, apparently.",
        "Your legs filed a complaint.",
        "Moving through space, at a cost.",
    ],
    "hobbies": [
        "You could've just stared at a wall. For free.",
        "Ah yes, the important stuff.",
        "Passions are expensive. And so are you.",
        "Money well spent. Maybe.",
    ],
    "investments": [
        "Future millionaire detected. Allegedly.",
        "Very responsible. Very suspicious.",
        "Number go up? Please?",
        "Bold of you to call this an investment.",
    ],
}

import random

def get_roast(category: str) -> str:
    options = SARCASM.get(category, ["Interesting financial decision."])
    return random.choice(options)


st.set_page_config(page_title="Review Invoice")

st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        h1, h2, h3 { font-family: 'DM Mono', monospace !important; }
        .expense-header {
            font-family: 'DM Mono', monospace;
            background: #1C1C1C;
            border-left: 4px solid #F59E0B;
            padding: 1rem 1.25rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }
        .expense-merchant {
            font-size: 1.1rem;
            color: #A8A29E;
            margin: 0 0 0.25rem 0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .expense-amount {
            font-size: 2.25rem;
            font-weight: 500;
            color: #F59E0B;
            margin: 0;
            line-height: 1.1;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.get("extracted"):
    st.switch_page("streamlit_app.py")

st.title("Review & Confirm")
st.caption("Double-check before you commit to your financial decisions.")

extracted = st.session_state["extracted"]

raw_date = extracted.get("date", "")
try:
    default_date = datetime.date.fromisoformat(raw_date) if raw_date else datetime.date.today()
except ValueError:
    default_date = datetime.date.today()

image_bytes = st.session_state.get("invoice_image")
mime_type = st.session_state.get("invoice_mime", "image/jpeg")

col_img, col_fields = st.columns([1, 1], gap="large")

with col_img:
    if image_bytes:
        st.image(image_bytes, caption="Your receipt. Exhibit A.", width='stretch')
    else:
        st.info("No image — you typed this in manually. Respect.")

with col_fields:
    merchant_display = extracted.get("place", "") or "Unknown"
    amount_display = float(extracted.get("value", 0.0))
    currency_display = extracted.get("currency", "EUR")

    st.markdown(
        f"""
        <div class="expense-header">
            <p class="expense-merchant">{merchant_display}</p>
            <p class="expense-amount">{currency_display} {amount_display:,.2f}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    date_value = st.date_input("Date", value=default_date)
    date = date_value.strftime("%Y-%m-%d")

    merchant = st.text_input("Merchant", value=extracted.get("place", ""))
    amount = st.number_input("Amount", value=float(extracted.get("value", 0.0)), min_value=0.0, step=1.00, format="%.2f")
    currency = st.text_input("Currency", value=extracted.get("currency", ""))

    categories = ["living costs", "food", "transportation", "hobbies", "investments"]
    extracted_category = extracted.get("category", categories[0])
    default_index = categories.index(extracted_category) if extracted_category in categories else 0
    category = st.selectbox("Category", categories, index=default_index)

    if st.button("Save", type="primary", width='stretch'):
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
        logic.append_entry(sheet, date, merchant, amount, currency, category)
        del st.session_state["extracted"]
        st.session_state.pop("invoice_image", None)
        st.session_state.pop("invoice_mime", None)
        st.toast(get_roast(category), icon="💸")
        st.switch_page("streamlit_app.py")
