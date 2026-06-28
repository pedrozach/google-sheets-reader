import base64
import json
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

import logic

load_dotenv()

SYSTEM_PROMPT = """You are a personal finance invoice classifier.

The user will upload an invoice, receipt, or bill image.

Your tasks are:

1. Read the image carefully.
2. Extract:
   - place (merchant/store/company name)
   - total value paid
   - currency
   - date (if available)
3. Categorize the invoice into EXACTLY ONE of these categories:
   - living costs
   - food
   - transportation
   - hobbies
   - investments
Category rules:
- Supermarkets, restaurants, cafés, food delivery => food
- Rent, utilities, electricity, water, internet, home expenses => living costs
- Uber, taxis, fuel, parking, metro, trains, buses => transportation
- Entertainment, games, books, cinema, sports, hobbies => hobbies
- Stocks, ETFs, brokers, crypto, savings investments => investments
Additional rules:
- Use the FINAL amount actually paid.
- Ignore VAT/subtotal unless it is the final amount.
- Normalize merchant names when possible.
  Example:
  - "UBER BV" -> "Uber"
  - "MCDONALD'S 1234" -> "McDonald's"
Return ONLY valid JSON.

Use this exact format:

{
  "place": "string",
  "value": number,
  "currency": "string",
  "date": "YYYY-MM-DD",
  "category": "living costs | food | transportation | hobbies | investments"
}

If a field is missing, use null.

Example output:

{
  "place": "Lidl",
  "value": 28.47,
  "currency": "EUR",
  "date": "2026-05-21",
  "category": "food"
}"""

st.set_page_config(page_title="Invoice Scanner")

st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        h1, h2, h3 { font-family: 'DM Mono', monospace !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Add Expense")

tab_upload, tab_manual = st.tabs(["Upload Invoice", "Manual Entry"])

with tab_upload:
    uploaded = st.file_uploader("Select an invoice image", type=["jpg", "jpeg", "png", "webp", "gif"])

    if uploaded is not None:
        image_bytes = uploaded.read()
        mime_type = uploaded.type or "image/jpeg"

        def _real_extractor(image_bytes: bytes, mime_type: str) -> dict:
            try:
                api_key = st.secrets.get("OPENAI_API_KEY") or os.environ["OPENAI_API_KEY"]
            except Exception:
                api_key = os.environ["OPENAI_API_KEY"]
            client = OpenAI(api_key=api_key)
            b64 = base64.standard_b64encode(image_bytes).decode()
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": SYSTEM_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=256,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)

        try:
            with st.spinner("Extracting invoice data..."):
                result = logic.extract(image_bytes, mime_type, _real_extractor)
            st.session_state["extracted"] = result
            st.session_state["invoice_image"] = image_bytes
            st.session_state["invoice_mime"] = mime_type
            st.switch_page("pages/review.py")
        except Exception as exc:
            st.error(f"Could not extract invoice data: {exc}")

with tab_manual:
    with st.form("manual_entry"):
        m_date = st.date_input("Date")
        m_merchant = st.text_input("Merchant")
        m_amount = st.number_input("Amount", min_value=0.0, step=0.10, format="%.2f")
        m_currency = st.text_input("Currency", value="EUR")
        categories = ["living costs", "food", "transportation", "hobbies", "investments"]
        m_category = st.selectbox("Category", categories)
        submitted = st.form_submit_button("Review")

    if submitted:
        st.session_state["extracted"] = {
            "date": m_date.strftime("%Y-%m-%d"),
            "place": m_merchant,
            "value": m_amount,
            "currency": m_currency,
            "category": m_category,
        }
        st.switch_page("pages/review.py")
