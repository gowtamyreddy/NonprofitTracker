"""Record the golden set from live API data, EIN-anchored.

Each case pins one organization's latest filing: year, revenue,
expenses, net assets, officer compensation. The eval re-fetches live
and compares exactly, so it catches field-mapping bugs and API drift.
If a newer filing lands, the case fails honestly with "re-record"
and this script refreshes it. Golden values are API-recorded, not
checked against filing PDFs by hand; the PDF link in each case is
how anyone else checks them.

Usage: python scripts/make_golden.py
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nonprofittracker import client  # noqa: E402

EINS = [
    530196605,  # American National Red Cross
    363673599,  # Feeding America
    521693387,  # World Wildlife Fund Inc
    351044585,  # American Lebanese Syrian Assoc Char Inc (ALSAC)
    133433452,  # Medecins Sans Frontieres Usa Inc
    135613797,  # American Heart Association Inc
    410706171,  # Goodwill Industries Inc
    350868167,  # Salvation Army
]

OUT = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "golden_cases.jsonl")


def main():
    cases = []
    for ein in EINS:
        data = client.get_org(ein)
        if not data or not data["filings"]:
            print(f"WARNING: no filings for {ein}, skipped")
            continue
        filing = data["filings"][0]
        cases.append({
            "ein": ein,
            "name": data["organization"]["name"],
            "tax_year": filing.get("tax_prd_yr"),
            "totrevenue": filing.get("totrevenue"),
            "totfuncexpns": filing.get("totfuncexpns"),
            "totnetassetend": filing.get("totnetassetend"),
            "compnsatncurrofcr": filing.get("compnsatncurrofcr"),
            "pdf_url": filing.get("pdf_url"),
            "recorded": datetime.date.today().isoformat(),
        })
        print(f"{ein} {cases[-1]['name']} year "
              f"{cases[-1]['tax_year']} rev {cases[-1]['totrevenue']}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as handle:
        for case in cases:
            handle.write(json.dumps(case) + "\n")
    print(f"Wrote {len(cases)} cases to {OUT}")


if __name__ == "__main__":
    main()
