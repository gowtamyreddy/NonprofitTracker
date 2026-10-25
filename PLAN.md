# Nonprofit Money Tracker: plan

## Goal
Search any nonprofit and see its money trail with filing citations,
so a donor can decide with numbers instead of blind trust.

## What it is not
Not a rating, not a recommendation, not a program-spending audit.
Program service EXPENSES are not in the ProPublica extracts, so v1
does not claim them. totprgmrevnue is program service REVENUE and is
labelled as such. A program-spending view would need full 990 XML or
PDF parsing and is a v2 investigation, not a v1 promise.

## Data (live, no key)
ProPublica Nonprofit Explorer API v2, IRS 990 filings. Search at
query time, nothing preloaded. Data is annual: numbers change when a
new filing lands. Search 404 means no matches. Name matches are
ambiguous, so the UI shows city/state and the user picks the EIN.

## Money trail (latest filing)
Revenue, expenses, surplus and margin, net assets, contributions
share, program revenue share, officer compensation and share,
fundraising net. Trend over up to 5 years. Every result links to its
filing PDF.

## Flags (review prompts, not ratings)
Deficit, deficit in 2 of 3 years, net assets falling two years
running, fundraising events losing money, officer pay above 5% of
expenses.

## Golden set (7 EIN-anchored cases)
data/golden_cases.jsonl pins each org's latest filing values as
recorded from the live API. The eval re-fetches live and compares
exactly, catching field-mapping bugs and API drift. If a newer filing
lands, the case fails honestly and scripts/make_golden.py refreshes
it. Golden values are API-recorded; the PDF link in each case is how
anyone checks them against the filing itself. An eighth candidate
(Salvation Army, Indianapolis EIN) was dropped: it has no filing
extracts in the API, so there is nothing to pin.

## Verification log
- 2026-10-25: API probed live (search + org + filing keys). No
  program-expenses field exists in extracts; spec corrected before
  building. Search 404 behavior confirmed (no-result queries).
- 2026-10-25: golden EINs verified by org fetch (name, city, filing
  presence, revenue scale). A plausible-looking American Cancer
  Society EIN was dropped: its latest filing showed revenue 123,885
  and expenses 0, wrong scale for the national org.
