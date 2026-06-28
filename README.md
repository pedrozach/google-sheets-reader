# Invoice Scanner & Spending Dashboard

A Streamlit app that extracts data from invoice images using GPT-4o vision and logs expenses to a Google Sheet. Includes a live pivot dashboard by month and category.

## Pages

- **Upload** — upload an invoice image; GPT-4o extracts merchant, amount, currency, date, and category.
- **Review** — confirm or edit the extracted fields before saving to the sheet.
- **Summary** — live spending breakdown by month and category, read directly from the sheet.

## Prerequisites

- Python 3.10+
- An OpenAI API key with access to `gpt-4o`
- A Google Cloud service account with the Sheets and Drive APIs enabled
- A Google Sheet with a worksheet named `expenses` and these column headers in row 1: `date`, `merchant`, `amount`, `currency`, `category`

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd google-sheets-reader
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Absolute path to your service account JSON file |
| `GOOGLE_SHEET_ID` | The ID from your Google Sheet URL: `docs.google.com/spreadsheets/d/<ID>/edit` |

### 3. Set up the Google service account

1. Go to [Google Cloud Console](https://console.cloud.google.com) and create a project.
2. Enable the **Google Sheets API** and **Google Drive API**.
3. Create a **Service Account** and download its JSON key file.
4. Set `GOOGLE_SERVICE_ACCOUNT_JSON` in `.env` to the absolute path of that file.
5. Open your Google Sheet, click **Share**, and share it with the service account email (e.g. `my-service-account@my-project.iam.gserviceaccount.com`) with Editor access.

### 4. Prepare the Google Sheet

In your sheet, rename the first worksheet to `expenses` and add these headers in row 1:

```
date | merchant | amount | currency | category
```

## Running the app

```bash
source .venv/bin/activate
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501`. The sidebar shows **Upload** and **Summary**. The Review page appears automatically after a successful upload.

## Running the tests

```bash
source .venv/bin/activate
pytest tests/test_logic.py -v
```

Tests cover `extract`, `append_entry`, and `compute_pivot` using plain Python fakes — no OpenAI or Google Sheets calls are made.

## Project structure

```
streamlit_app.py          # Upload page (entry point)
pages/
  review.py               # Review & edit page
  summary.py              # Spending pivot dashboard
logic.py                  # Pure functions: extract, append_entry, compute_pivot
tests/
  test_logic.py           # Unit tests for logic.py
.env.example              # Environment variable template
requirements.txt          # Python dependencies
.agents/skills/
  finance-categorizer/    # GPT-4o prompt and output schema
```
