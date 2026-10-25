"""Live client for the ProPublica Nonprofit Explorer API (v2).

No API key, no login. Search returns 404 when nothing matches, which
we treat as an empty result, not an error. Filings data is annual:
a nonprofit's numbers change when its new 990 lands, not daily.
"""

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

try:
    import certifi
except ImportError:
    certifi = None

BASE_URL = "https://projects.propublica.org/nonprofits/api/v2"
USER_AGENT = "NonprofitTracker/1.0 (research demo)"


def _ssl_context():
    """Verify certificates against a real CA bundle.

    The python.org installer for macOS ships Python without root
    certificates, so the default context fails every HTTPS request
    there with CERTIFICATE_VERIFY_FAILED. certifi supplies the
    maintained Mozilla bundle; verification stays fully on, nothing
    is bypassed. Without certifi, fall back to the default context.
    """
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30,
                                    context=_ssl_context()) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def search_orgs(query, limit=10):
    """Search by name. Returns top matches with EIN, city, state.

    Name matches are ambiguous (many chapters share a name), so callers
    must show city/state and let the user pick the EIN. Never assume
    the top hit is the national organization.
    """
    data = _get_json(f"{BASE_URL}/search.json?q={urllib.parse.quote(query)}")
    if not data:
        return []
    out = []
    for org in data.get("organizations", [])[:limit]:
        out.append({"ein": org["ein"], "name": org["name"],
                    "city": org.get("city"), "state": org.get("state"),
                    "score": org.get("score")})
    return out


def get_org(ein):
    """Fetch one organization with its filings, newest year first."""
    data = _get_json(f"{BASE_URL}/organizations/{ein}.json")
    if not data:
        return None
    filings = sorted(data.get("filings_with_data") or [],
                     key=lambda f: f.get("tax_prd_yr") or 0, reverse=True)
    return {"organization": data["organization"], "filings": filings}
