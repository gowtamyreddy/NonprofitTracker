# Nonprofit Money Tracker

Search any nonprofit and see its money trail, with filing citations.
Not a rating. Not a recommendation. Just the numbers, with receipts,
so a donor can decide for themselves.

## What it shows (latest 990 filing)
Revenue, expenses, surplus and margin, net assets, contributions
share, program revenue share, officer compensation and its share of
expenses, fundraising net, plus a 5-year trend and flags for review
(deficit, falling reserves, fundraising losses, high officer pay).
Every result links to its filing PDF.

## What it does not show
Program service spending. The ProPublica filing extracts do not
carry program service expenses, so this tool does not invent them.
`totprgmrevnue` is program service revenue (money earned from
programs) and is labelled as such wherever it appears.

## Data
ProPublica Nonprofit Explorer API v2, IRS 990 filings. No API key.
Queries run live at search time; nothing is preloaded. Data is
annual: numbers change when a new filing lands. Name matches are
ambiguous (many chapters share a name), so results show city and
state and you pick by EIN.

## Run it

CLI search and detail:

```
python -m nonprofittracker.cli search "Red Cross"
python -m nonprofittracker.cli show 530196605
```

Dashboard:

```
python app.py
```

Eval (7 EIN-anchored golden cases, re-fetched live):

```
python -m nonprofittracker.cli eval
```

Tests (offline):

```
python -m unittest tests.test_nonprofittracker -v
```

## Golden set
`data/golden_cases.jsonl` pins each organization's latest filing
values as recorded from the live API. The eval compares exactly, so
it catches field-mapping bugs and API drift. If a newer filing
lands, the case fails honestly and `scripts/make_golden.py`
refreshes it.
