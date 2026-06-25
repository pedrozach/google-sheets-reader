#!/usr/bin/env python3
"""Session 3 - Quote -> Haiku

Generates a random quote and uses the OpenAI API to create a haiku from it.

Usage:
  export OPENAI_API_KEY="..."
  python3 session-3/solutions/3_01.py
  python3 session-3/solutions/3_01.py --save out.txt
"""

import os
import random
import sys

try:
    from openai import OpenAI
except Exception:
    print("Missing dependency 'openai'. Run: pip install -r requirements.txt")
    raise

QUOTES = [
    "The only way to do great work is to love what you do. - Steve Jobs",
    "Life is what happens when you're busy making other plans. - John Lennon",
    "Do not go where the path may lead, go instead where there is no path. - Ralph Waldo Emerson",
    "In the middle of every difficulty lies opportunity. - Albert Einstein",
    "Happiness is not something ready made. It comes from your own actions. - Dalai Lama",
]


def choose_quote():
    return random.choice(QUOTES)


def make_haiku_from_quote(quote: str, model: str = "gpt-3.5-turbo") -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set — export it before running the script.")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = (
        "Create a haiku (three lines with 5-7-5 syllable structure) inspired by the following quote. "
        "Return only the haiku, no extra commentary.\n\nQuote:\n" + quote
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=60,
    )

    # New client returns objects with attribute access
    try:
        haiku = resp.choices[0].message.content.strip()
    except Exception:
        # Fallback to dict-like access for older client compat
        haiku = resp["choices"][0]["message"]["content"].strip()

    return haiku


def main(save: str | None = None) -> None:
    quote = choose_quote()
    print("Quote:", quote)

    try:
        haiku = make_haiku_from_quote(quote)
    except Exception as e:
        print("Error creating haiku:", e)
        sys.exit(1)

    print("\nHaiku:\n" + haiku)

    if save:
        with open(save, "w", encoding="utf-8") as f:
            f.write(f"Quote: {quote}\n\nHaiku:\n{haiku}\n")
        print(f"\nSaved output to {save}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Generate a haiku from a random quote using OpenAI API.")
    p.add_argument("--save", "-s", help="Path to save the output (optional)")
    p.add_argument("--model", "-m", help="OpenAI model to use", default="gpt-3.5-turbo")
    args = p.parse_args()

    # allow passing model via env or CLI
    if args.model:
        model = args.model
    else:
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    try:
        main(save=args.save)
    except Exception as exc:
        print("Fatal:", exc)
        sys.exit(1)
