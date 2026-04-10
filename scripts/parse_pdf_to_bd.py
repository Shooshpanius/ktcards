#!/usr/bin/env python3
"""
Parse a Kill Team data-card PDF into the .bd JSON format using pdfplumber + OpenAI.

Usage:
    python parse_pdf_to_bd.py <path/to/TeamName.pdf> [<path/to/output/TeamName.bd>]

If the output path is omitted, the .bd file is written next to the PDF.

Requires:
    OPENAI_API_KEY environment variable.
    pip install pdfplumber openai
"""

import argparse
import json
import os
import sys

import pdfplumber
from openai import OpenAI


BD_SCHEMA = """
{
  "teamName": "string",
  "operatives": [
    {
      "name": "string",
      "keywords": ["string"],
      "movement": "string (e.g. '3\"')",
      "actionPointLimit": "int",
      "groupActivations": "int",
      "defence": "int",
      "save": "int (numeric value of the save roll, e.g. 4 for 4+)",
      "wounds": "int",
      "notes": "string or null",
      "abilities": [
        { "name": "string", "description": "string" }
      ],
      "attacks": [
        {
          "name": "string",
          "type": "Melee or Ranged",
          "attacks": "int",
          "hitSkill": "int (numeric, e.g. 3 for 3+)",
          "damage": "string",
          "criticalDamage": "string",
          "specialRules": "string or null"
        }
      ]
    }
  ],
  "factionRules": [
    { "name": "string", "description": "string" }
  ],
  "markersTokens": [
    { "name": "string", "description": "string" }
  ],
  "strategyPloys": [
    { "name": "string", "cpCost": "int", "description": "string" }
  ],
  "firefightPloys": [
    { "name": "string", "cpCost": "int", "description": "string" }
  ],
  "factionEquipment": [
    {
      "name": "string",
      "epCost": "int",
      "description": "string",
      "restrictions": "string or null"
    }
  ]
}
"""

SYSTEM_PROMPT = f"""You are a data extraction assistant for Warhammer 40,000 Kill Team.
You will receive the raw text extracted from a Kill Team data-card PDF.
Your job is to extract all game data and return it as valid JSON matching exactly this schema:

{BD_SCHEMA}

Rules:
- Return ONLY raw JSON, no markdown fences, no explanation.
- All numeric fields (actionPointLimit, groupActivations, defence, save, wounds, attacks, hitSkill, cpCost, epCost) must be integers.
- "type" for attacks must be exactly "Melee" or "Ranged".
- If a section is absent in the PDF, use an empty array [].
- Preserve the exact text of names and descriptions.
- Do NOT include teamComposition or any fields not listed in the schema.
"""


def extract_text(pdf_path: str) -> str:
    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if page_text:
                text_pages.append(page_text)
    return "\n\n--- PAGE BREAK ---\n\n".join(text_pages)


def parse_with_openai(text: str, team_name: str) -> dict:
    client = OpenAI()

    user_content = (
        f"Team name hint: {team_name}\n\n"
        "Here is the extracted PDF text:\n\n"
        f"{text}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description="Parse Kill Team PDF to .bd JSON")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "output_path",
        nargs="?",
        default=None,
        help="Output .bd file path (default: same dir as PDF, same stem + .bd)",
    )
    args = parser.parse_args()

    pdf_path = os.path.abspath(args.pdf_path)
    if not os.path.isfile(pdf_path):
        print(f"ERROR: PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    team_name = os.path.splitext(os.path.basename(pdf_path))[0]

    if args.output_path:
        output_path = os.path.abspath(args.output_path)
    else:
        output_path = os.path.join(os.path.dirname(pdf_path), f"{team_name}.bd")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting text from: {pdf_path}")
    text = extract_text(pdf_path)
    if not text.strip():
        print("ERROR: No text could be extracted from the PDF.", file=sys.stderr)
        sys.exit(1)
    print(f"Extracted {len(text)} characters of text.")

    print("Sending to OpenAI for structured extraction...")
    data = parse_with_openai(text, team_name)

    # Ensure teamName is set
    if not data.get("teamName"):
        data["teamName"] = team_name

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
