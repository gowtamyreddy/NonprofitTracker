"""Gradio dashboard: search a nonprofit, see its money trail live."""

import re

import gradio as gr
import pandas as pd

from nonprofittracker import client, money


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


def _trend_frames(metrics):
    """Chart data for the trend years: revenue vs expenses lines,
    surplus bars. Years are strings so the axis stays ordinal.
    Missing values are dropped from the charts, not zero-filled."""
    series = money.trend_series(metrics)
    line_rows = []
    for year, revenue, expenses in zip(series["years"], series["revenue"],
                                       series["expenses"]):
        if revenue is not None:
            line_rows.append({"year": str(year), "amount": revenue,
                              "series": "Revenue"})
        if expenses is not None:
            line_rows.append({"year": str(year), "amount": expenses,
                              "series": "Expenses"})
    bar_rows = [{"year": str(year), "surplus": surplus}
                for year, surplus in zip(series["years"], series["surplus"])
                if surplus is not None]
    return pd.DataFrame(line_rows), pd.DataFrame(bar_rows)


def do_search(query):
    results = client.search_orgs(query)
    if not results:
        return (gr.update(choices=[], value=None),
                "No organizations found. Try the legal name, not the "
                "brand. Many chapters share a name, so city and state "
                "are shown to tell them apart.")
    choices = [f"{r['name']} ({r['city'] or ''}, {r['state'] or ''}) "
               f"[{r['ein']}]" for r in results]
    # No auto-select: the first result is often a small chapter, and
    # loading it before the user picks shows the wrong organization.
    return gr.update(choices=choices, value=None), \
        "Pick the organization you want from the list."


def do_detail(choice):
    if not choice:
        return "Search first, then pick an organization.", None, None, ""
    match = re.search(r"\[(\d+)\]\s*$", choice)
    if not match:
        return "Could not read the EIN from that choice.", None, None, ""
    data = client.get_org(match.group(1))
    if not data:
        return "No organization found for that EIN.", None, None, ""
    org = data["organization"]
    metrics = [money.metrics_for_filing(f) for f in data["filings"]]
    if not metrics:
        return (f"## {org['name']}\n\nNo filing data available for "
                f"this organization.", None, None, "")
    latest = metrics[0]
    latest_link = (f" ([Filing PDF]({latest['pdf_url']}))"
                   if latest["pdf_url"] else "")
    lines = [f"## {org['name']} ({org['city']}, {org['state']})",
             f"EIN {org['ein']} | Latest filing: {latest['year']}"
             f"{latest_link}",
             "",
             "Source: IRS Form 990, tax year "
             f"{latest['year']}, via ProPublica Nonprofit Explorer. "
             "Every number in the money trail below comes from that "
             "filing.",
             "",
             "Note: ProPublica allows one PDF download per minute. "
             "If a link shows a 429 error, wait a minute and click "
             "again. The header link and the latest trend row link "
             "to the same filing.",
             "",
             "### Money trail (latest filing)",
             f"- Revenue: {_dollars(latest['revenue'])}",
             f"- Expenses: {_dollars(latest['expenses'])}",
             f"- Surplus: {_dollars(latest['surplus'])} "
             f"(margin {_pct(latest['margin'])})",
             f"- Net assets: {_dollars(latest['net_assets'])}",
             f"- Contributions share: "
             f"{_pct(latest['contributions_share'])}",
             "- Program revenue share (money earned from programs, "
             f"not spending): {_pct(latest['program_revenue_share'])}",
             f"- Officer compensation: {_dollars(latest['exec_comp'])} "
             f"({_pct(latest['exec_comp_share'])} of expenses)",
             f"- Fundraising net: {_dollars(latest['fundraising_net'])}",
             ""]
    flags = money.flags_for_history(metrics)
    lines.append("### Flags for review (not a rating)")
    if flags:
        lines += [f"- {flag['text']}" for flag in flags]
    else:
        lines.append("- None in the latest filing.")
    trend_lines = ["### Trend"]
    for metric in metrics[:5]:
        pdf = (f" ([filing PDF]({metric['pdf_url']}))"
               if metric["pdf_url"] else "")
        trend_lines.append(f"- {metric['year']}: revenue "
                           f"{_dollars(metric['revenue'])}, expenses "
                           f"{_dollars(metric['expenses'])}, surplus "
                           f"{_dollars(metric['surplus'])}{pdf}")
    line_df, bar_df = _trend_frames(metrics[:5])
    return "\n".join(lines), line_df, bar_df, "\n".join(trend_lines)


with gr.Blocks(title="Nonprofit Money Tracker") as demo:
    gr.Markdown("# Nonprofit Money Tracker\n\nSearch any nonprofit "
                 "and see its money trail, with filing citations. "
                 "Every number comes from a filed 990 at search time. "
                 "Flags are review prompts, not ratings.")
    query = gr.Textbox(label="Nonprofit name",
                       placeholder="American National Red Cross")
    search_btn = gr.Button("Search")
    search_note = gr.Markdown("")
    choice = gr.Dropdown(label="Pick the organization", choices=[])
    detail = gr.Markdown("")
    line_plot = gr.LinePlot(x="year", y="amount", color="series",
                            title="Revenue vs expenses")
    bar_plot = gr.BarPlot(x="year", y="surplus",
                          title="Surplus by year")
    trend = gr.Markdown("")
    search_btn.click(do_search, inputs=query,
                     outputs=[choice, search_note])
    choice.change(do_detail, inputs=choice,
                  outputs=[detail, line_plot, bar_plot, trend])

if __name__ == "__main__":
    demo.launch()
