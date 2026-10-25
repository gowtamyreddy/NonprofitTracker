"""CLI: search, show, eval."""

import argparse
import json
import os

from nonprofittracker import client, money

GOLDEN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "golden_cases.jsonl")


def _dollars(value):
    if value is None:
        return "not reported"
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1e9:
        return f"{sign}${value / 1e9:.2f}B"
    if value >= 1e6:
        return f"{sign}${value / 1e6:.2f}M"
    if value >= 1e3:
        return f"{sign}${value / 1e3:.0f}K"
    return f"{sign}${value:.0f}"


def _pct(value):
    return "not reported" if value is None else f"{value * 100:.1f}%"


def cmd_search(args):
    results = client.search_orgs(args.query)
    if not results:
        print("No organizations found. Try the legal name, not the brand.")
        return
    for org in results:
        print(f"{org['ein']}  {org['name']}  "
              f"({org['city'] or ''}, {org['state'] or ''})")


def cmd_show(args):
    data = client.get_org(args.ein)
    if not data:
        print(f"No organization found for EIN {args.ein}.")
        return
    org = data["organization"]
    print(f"{org['name']}  ({org['city']}, {org['state']})  "
          f"EIN {org['ein']}")
    metrics = [money.metrics_for_filing(f) for f in data["filings"]]
    if not metrics:
        print("No filing data available for this organization.")
        return
    latest = metrics[0]
    print(f"Latest filing: {latest['year']}")
    print(f"  Revenue: {_dollars(latest['revenue'])}")
    print(f"  Expenses: {_dollars(latest['expenses'])}")
    print(f"  Surplus: {_dollars(latest['surplus'])} "
          f"(margin {_pct(latest['margin'])})")
    print(f"  Net assets: {_dollars(latest['net_assets'])}")
    print(f"  Contributions share: {_pct(latest['contributions_share'])}")
    print(f"  Program revenue share (not spending): "
          f"{_pct(latest['program_revenue_share'])}")
    print(f"  Officer compensation: {_dollars(latest['exec_comp'])} "
          f"({_pct(latest['exec_comp_share'])} of expenses)")
    print(f"  Fundraising net: {_dollars(latest['fundraising_net'])}")
    for flag in money.flags_for_history(metrics):
        print(f"  Flag: {flag['text']}")
    print("  Trend (year, revenue, expenses, surplus):")
    for metric in metrics[:5]:
        print(f"    {metric['year']}  {_dollars(metric['revenue'])}  "
              f"{_dollars(metric['expenses'])}  "
              f"{_dollars(metric['surplus'])}")
    if latest["pdf_url"]:
        print(f"  Filing PDF: {latest['pdf_url']}")


def cmd_eval(args):
    cases = []
    with open(args.golden or GOLDEN) as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    passed = 0
    for case in cases:
        data = client.get_org(case["ein"])
        if not data or not data["filings"]:
            print(f"{case['ein']} FAIL: no live filings")
            continue
        filing = data["filings"][0]
        live = money.metrics_for_filing(filing)
        mismatches = []
        if filing.get("tax_prd_yr") != case["tax_year"]:
            mismatches.append(
                f"year live {filing.get('tax_prd_yr')} vs golden "
                f"{case['tax_year']} (a newer filing landed; re-record)")
        for key in ("totrevenue", "totfuncexpns", "totnetassetend",
                    "compnsatncurrofcr"):
            if filing.get(key) != case.get(key):
                mismatches.append(f"{key} live {filing.get(key)} vs "
                                  f"golden {case.get(key)}")
        if live["revenue"] is not None and live["expenses"] is not None \
                and live["surplus"] != live["revenue"] - live["expenses"]:
            mismatches.append("surplus math broken")
        ok = not mismatches
        passed += ok
        print(f"{case['ein']} {'PASS' if ok else 'FAIL'}: "
              f"{case['name']} ({'; '.join(mismatches) or 'matches'})")
    print(f"Pass rate: {passed}/{len(cases)}")


def main():
    parser = argparse.ArgumentParser(prog="nonprofittracker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("search")
    p.add_argument("query")
    p.set_defaults(fn=cmd_search)
    p = sub.add_parser("show")
    p.add_argument("ein")
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("eval")
    p.add_argument("--golden")
    p.set_defaults(fn=cmd_eval)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
