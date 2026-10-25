"""Money trail math from a filed 990 extract.

Only fields the ProPublica extracts actually carry. Notably absent:
program service EXPENSES. totprgmrevnue is program service REVENUE
(money earned from programs), which is a different thing and is
labelled as such everywhere it appears. Any claim about program
spending would need the full 990 XML or PDF, which is out of scope
for v1. Flags are review prompts, never ratings or verdicts.
"""


def _num(filing, key):
    value = filing.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _share(part, whole):
    if part is None or not whole:
        return None
    return part / whole


def metrics_for_filing(filing):
    """Compute the money trail for one filing. Missing fields -> None."""
    revenue = _num(filing, "totrevenue")
    expenses = _num(filing, "totfuncexpns")
    surplus = None
    if revenue is not None and expenses is not None:
        surplus = revenue - expenses
    return {
        "year": filing.get("tax_prd_yr"),
        "pdf_url": filing.get("pdf_url"),
        "revenue": revenue,
        "expenses": expenses,
        "surplus": surplus,
        "margin": _share(surplus, revenue),
        "net_assets": _num(filing, "totnetassetend"),
        "contributions": _num(filing, "totcntrbgfts"),
        "contributions_share": _share(_num(filing, "totcntrbgfts"),
                                      revenue),
        "program_revenue": _num(filing, "totprgmrevnue"),
        "program_revenue_share": _share(_num(filing, "totprgmrevnue"),
                                        revenue),
        "exec_comp": _num(filing, "compnsatncurrofcr"),
        "exec_comp_share": _share(_num(filing, "compnsatncurrofcr"),
                                  expenses),
        "fundraising_net": _num(filing, "netincfndrsng"),
        "fundraising_gross": _num(filing, "grsincfndrsng"),
        "prof_fundraising": _num(filing, "profndraising"),
    }


def flags_for_history(metrics):
    """Review flags from the latest filing plus trend. Not a rating.

    metrics: newest-first list from metrics_for_filing.
    """
    if not metrics:
        return []
    latest = metrics[0]
    flags = []
    if latest["revenue"] is not None and latest["expenses"] is not None \
            and latest["expenses"] > latest["revenue"]:
        flags.append({"code": "deficit",
                      "text": "Spent more than it raised in the latest "
                              "filing year."})
    recent = [m for m in metrics[:3]
              if m["revenue"] is not None and m["expenses"] is not None]
    if len(recent) == 3 and sum(1 for m in recent
                                if m["expenses"] > m["revenue"]) >= 2:
        flags.append({"code": "deficit_2of3",
                      "text": "Deficit in at least 2 of the last 3 "
                              "filing years."})
    assets = [m["net_assets"] for m in metrics[:3]
              if m["net_assets"] is not None]
    if len(assets) == 3 and assets[0] < assets[1] < assets[2]:
        flags.append({"code": "reserves_falling",
                      "text": "Net assets fell two years running."})
    if latest["fundraising_net"] is not None \
            and latest["fundraising_net"] < 0:
        flags.append({"code": "fundraising_loss",
                      "text": "Fundraising events lost money in the "
                              "latest filing year."})
    if latest["exec_comp_share"] is not None \
            and latest["exec_comp_share"] > 0.05:
        flags.append({"code": "exec_pay_high",
                      "text": "Officer compensation above 5% of total "
                              "expenses."})
    return flags


def trend_series(metrics):
    """Chronological trend data for charts, oldest first.

    Metrics arrive newest-first; the chart reads oldest to newest.
    Missing values stay None so charts skip them instead of
    plotting a false zero.
    """
    ordered = list(reversed(metrics))
    return {"years": [m["year"] for m in ordered],
            "revenue": [m["revenue"] for m in ordered],
            "expenses": [m["expenses"] for m in ordered],
            "surplus": [m["surplus"] for m in ordered]}
