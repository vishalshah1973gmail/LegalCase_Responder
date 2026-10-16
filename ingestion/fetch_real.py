"""Optional: fetch REAL, freely available property-law opinions into /data/cases.

This is a best-effort supplement to the synthetic corpus. It uses the free,
public CourtListener REST API (https://www.courtlistener.com/help/api/rest/),
which serves public-domain U.S. court opinions. An API token is optional but
raises the rate limit; set COURTLISTENER_TOKEN in your .env if you have one.

The build shipped with this project was generated in a sandbox with no outbound
network access, so the corpus is 100% synthetic. Run this script from a machine
with normal internet access to add real cases; every case it writes is tagged
``source: "real"`` and carries its CourtListener URL for attribution.

Usage:
    python ingestion/fetch_real.py --per-query 5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CASES_DIR  # noqa: E402

API = "https://www.courtlistener.com/api/rest/v4"

QUERIES = {
    "landlord_tenant": "landlord tenant implied warranty of habitability lease",
    "easement": "easement by necessity prescriptive easement servient estate",
    "boundary_title": "boundary dispute quiet title acquiescence survey monument",
    "hoa_covenant": "restrictive covenant homeowners association declaration enforce",
    "foreclosure": "mortgage foreclosure acceleration notice of default standing note",
    "adverse_possession": "adverse possession open notorious hostile continuous",
    "zoning": "zoning variance unnecessary hardship board of adjustment",
    "lease_rider": "commercial lease rider percentage rent holdover assignment consent",
    "eminent_domain": "eminent domain just compensation severance damages taking",
    "water_rights": "riparian rights water diversion reasonable use groundwater",
}

_PARA_SPLIT = re.compile(r"\n\s*\n+")
_TAG = re.compile(r"<[^>]+>")


def _get(url: str, token: str | None) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "LegalCase-Responder/1.0"})
    if token:
        req.add_header("Authorization", f"Token {token}")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def _clean(html_or_text: str) -> str:
    txt = _TAG.sub(" ", html_or_text or "")
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    return re.sub(r"[ \t]+", " ", txt).strip()


def _sections(body: str) -> List[Dict[str, Any]]:
    """Split an opinion into ordered numbered paragraphs."""
    paras = [p.strip() for p in _PARA_SPLIT.split(body) if len(p.strip()) > 120]
    out = []
    for i, p in enumerate(paras, start=1):
        out.append({
            "section_type": "paragraph",
            "section_number": str(i),
            "heading": f"Paragraph {i}",
            "order": i,
            "text": p,
        })
    return out


def fetch(case_type: str, query: str, limit: int, token: str | None) -> List[Dict[str, Any]]:
    url = f"{API}/search/?" + urllib.parse.urlencode(
        {"q": query, "type": "o", "order_by": "score desc"})
    data = _get(url, token)
    cases: List[Dict[str, Any]] = []
    for res in data.get("results", [])[:limit]:
        cluster_id = res.get("cluster_id") or res.get("id")
        try:
            ops = _get(f"{API}/opinions/?cluster={cluster_id}", token)
        except urllib.error.HTTPError:
            continue
        body = ""
        for op in ops.get("results", []):
            body = op.get("plain_text") or _clean(op.get("html_with_citations")
                                                  or op.get("html") or "")
            if body:
                break
        secs = _sections(body)
        if len(secs) < 4:
            continue
        cases.append({
            "case_id": f"REAL-CL-{cluster_id}",
            "case_name": res.get("caseName", "Unknown"),
            "full_caption": res.get("caseName", "Unknown"),
            "court": res.get("court", "Unknown court"),
            "jurisdiction": res.get("court_citation_string") or res.get("court", ""),
            "date": (res.get("dateFiled") or "")[:10],
            "case_type": case_type,
            "case_type_label": case_type.replace("_", " ").title(),
            "source": "real",
            "docket_number": res.get("docketNumber", ""),
            "property_address": "",
            "source_url": "https://www.courtlistener.com" + (res.get("absolute_url") or ""),
            "sections": secs,
        })
        time.sleep(0.5)
    return cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-query", type=int, default=5,
                    help="max real cases to keep per case type")
    args = ap.parse_args()
    token = os.getenv("COURTLISTENER_TOKEN") or None

    total = 0
    for ctype, q in QUERIES.items():
        try:
            cases = fetch(ctype, q, args.per_query, token)
        except Exception as exc:  # network blocked, rate limited, schema drift
            print(f"[skip] {ctype}: {type(exc).__name__}: {exc}")
            continue
        for c in cases:
            (CASES_DIR / f"{c['case_id']}.json").write_text(
                json.dumps(c, indent=2, ensure_ascii=False), encoding="utf-8")
            total += 1
        print(f"[ok]   {ctype}: wrote {len(cases)} real cases")

    print(f"\nDone. {total} real cases written to {CASES_DIR}.")
    if total == 0:
        print("No real cases retrieved — the corpus stays fully synthetic. "
              "This is the documented fallback; see README.")
    else:
        print("Re-run ingestion (GUI 1) to index the new cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
