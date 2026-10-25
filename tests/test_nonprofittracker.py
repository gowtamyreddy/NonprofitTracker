"""Offline tests: money math, flags, and client parsing."""

import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nonprofittracker import client, money


def filing(**overrides):
    base = {"tax_prd_yr": 2023, "totrevenue": 1000,
            "totfuncexpns": 800, "totnetassetend": 500,
            "totcntrbgfts": 400, "totprgmrevnue": 300,
            "compnsatncurrofcr": 10, "netincfndrsng": 5,
            "grsincfndrsng": 100, "profndraising": 2,
            "pdf_url": "https://example.org/filing.pdf"}
    base.update(overrides)
    return base


class MoneyTests(unittest.TestCase):
    def test_surplus_margin_shares(self):
        metric = money.metrics_for_filing(filing())
        self.assertEqual(metric["surplus"], 200)
        self.assertAlmostEqual(metric["margin"], 0.2)
        self.assertAlmostEqual(metric["contributions_share"], 0.4)
        self.assertAlmostEqual(metric["program_revenue_share"], 0.3)
        self.assertAlmostEqual(metric["exec_comp_share"], 0.0125)

    def test_zero_revenue_gives_none_shares(self):
        metric = money.metrics_for_filing(filing(totrevenue=0))
        self.assertIsNone(metric["margin"])
        self.assertIsNone(metric["contributions_share"])

    def test_missing_fields_give_none(self):
        metric = money.metrics_for_filing({"tax_prd_yr": 2023})
        self.assertIsNone(metric["revenue"])
        self.assertIsNone(metric["surplus"])
        self.assertEqual(money.flags_for_history([metric]), [])

    def test_deficit_flags(self):
        metric = money.metrics_for_filing(
            filing(totrevenue=800, totfuncexpns=1000))
        codes = [f["code"] for f in money.flags_for_history([metric])]
        self.assertIn("deficit", codes)

    def test_deficit_2of3_and_reserves_falling(self):
        history = [money.metrics_for_filing(f) for f in [
            filing(tax_prd_yr=2023, totrevenue=800, totfuncexpns=1000,
                   totnetassetend=80),
            filing(tax_prd_yr=2022, totrevenue=800, totfuncexpns=1000,
                   totnetassetend=90),
            filing(tax_prd_yr=2021, totrevenue=1000, totfuncexpns=800,
                   totnetassetend=100),
        ]]
        codes = [f["code"] for f in money.flags_for_history(history)]
        self.assertIn("deficit", codes)
        self.assertIn("deficit_2of3", codes)
        self.assertIn("reserves_falling", codes)

    def test_fundraising_loss_and_exec_pay_flags(self):
        metric = money.metrics_for_filing(
            filing(netincfndrsng=-5, compnsatncurrofcr=60,
                   totfuncexpns=1000))
        codes = [f["code"] for f in money.flags_for_history([metric])]
        self.assertIn("fundraising_loss", codes)
        self.assertIn("exec_pay_high", codes)

    def test_clean_case_has_no_flags(self):
        metric = money.metrics_for_filing(filing())
        self.assertEqual(money.flags_for_history([metric]), [])

    def test_trend_series_is_chronological(self):
        history = [money.metrics_for_filing(f) for f in [
            filing(tax_prd_yr=2023, totrevenue=1000, totfuncexpns=800),
            filing(tax_prd_yr=2022, totrevenue=900, totfuncexpns=850),
            filing(tax_prd_yr=2021, totrevenue=800, totfuncexpns=700),
        ]]
        series = money.trend_series(history)
        self.assertEqual(series["years"], [2021, 2022, 2023])
        self.assertEqual(series["revenue"], [800, 900, 1000])
        self.assertEqual(series["surplus"], [100, 50, 200])

    def test_trend_series_keeps_missing_values(self):
        series = money.trend_series([money.metrics_for_filing(
            {"tax_prd_yr": 2023})])
        self.assertEqual(series["revenue"], [None])
        self.assertEqual(money.trend_series([]),
                         {"years": [], "revenue": [], "expenses": [],
                          "surplus": []})


class ClientTests(unittest.TestCase):
    def test_search_parses_results(self):
        stub = {"total_results": 2, "organizations": [
            {"ein": 123, "name": "Example Org", "city": "Austin",
             "state": "TX", "score": 9.5}]}
        with mock.patch.object(client, "_get_json", return_value=stub):
            results = client.search_orgs("example")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ein"], 123)

    def test_search_404_means_empty(self):
        def raise_404(url, **kwargs):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        with mock.patch.object(client.urllib.request, "urlopen",
                               side_effect=raise_404):
            self.assertEqual(client.search_orgs("nothinghere"), [])

    def test_requests_verify_tls_with_a_context(self):
        import io
        import ssl
        from unittest.mock import MagicMock

        response = MagicMock()
        response.__enter__.return_value = io.StringIO(
            '{"organizations": []}')
        with mock.patch.object(client.urllib.request, "urlopen",
                               return_value=response) as urlopen:
            result = client._get_json("https://example.org/x.json")
        self.assertEqual(result, {"organizations": []})
        self.assertIsInstance(urlopen.call_args.kwargs.get("context"),
                              ssl.SSLContext)

    def test_get_org_sorts_filings_newest_first(self):
        stub = {"organization": {"ein": 1, "name": "Org"},
                "filings_with_data": [
                    {"tax_prd_yr": 2021, "totrevenue": 5},
                    {"tax_prd_yr": 2023, "totrevenue": 7}]}
        with mock.patch.object(client, "_get_json", return_value=stub):
            data = client.get_org(1)
        self.assertEqual(data["filings"][0]["tax_prd_yr"], 2023)


if __name__ == "__main__":
    unittest.main()
