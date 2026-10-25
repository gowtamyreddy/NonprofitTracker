"""Gradio dashboard: search a nonprofit, see its money trail live."""

import re

import gradio as gr

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


def do_search(query):
    results = client.search_orgs(query)
    if not results:
        return (gr.update(choices=[], value=None),
                "No organizations found. Try the legal name, not the "
                "brand. Many chapters share a name, so city and state "
                "are shown to tell them apart.")
    choices = [f"{r['name']} ({r['city'] or ''}, {r['state'] or ''}) "
               f"[{r['ein']}]" for r in results]
    return gr.update(choices=choices, value=choices[0]), ""


def do_detail(choice):
    if not choice:
        return "Search first, then pick an organization."
    match = re.search(r"\[(\d+)\]\s*$", choice)
    if not match:
        return "Could not read the EIN from that choice."
    data = client.get_org(match.group(1))
    if not data:
        return "No organization found for that EIN."
    org = data["organization"]
    metrics = [money.metrics_for_filing(f) for f in data["filings"]]
    if not metrics:
        return (f"## {org['name']}\n\nNo filing data available for "
                f"this organization.")
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
    lines += ["", "### Trend"]
    for metric in metrics[:5]:
        pdf = (f" ([filing PDF]({metric['pdf_url']}))"
               if metric["pdf_url"] else "")
        lines.append(f"- {metric['year']}: revenue "
                     f"{_dollars(metric['revenue'])}, expenses "
                     f"{_dollars(metric['expenses'])}, surplus "
                     f"{_dollars(metric['surplus'])}{pdf}")
    return "\n".join(lines)


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
    search_btn.click(do_search, inputs=query,
                     outputs=[choice, search_note])
    choice.change(do_detail, inputs=choice, outputs=detail)

if __name__ == "__main__":
    demo.launch()
