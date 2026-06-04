import asyncio
from html.parser import HTMLParser
import json
import re
from typing import Optional
from urllib.parse import urljoin

import httpx
from fastmcp import FastMCP

GSA_IFB_URL = "https://gsa.doa.guam.gov/invitation-for-bid/"
REQUEST_TIMEOUT_SECONDS = 12

# STEP 1: Name your server - this shows up when AI tools connect to it.
mcp = FastMCP("Guam GSA Procurement")


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: Optional[str] = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        self._current_href = attrs_dict.get("href")
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._current_href:
            return
        title = normalize_space(" ".join(self._text_parts))
        if title:
            self.links.append({"title": title, "url": self._current_href})
        self._current_href = None
        self._text_parts = []


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def document_year(title: str, url: str) -> Optional[int]:
    match = re.search(r"\b(20\d{2})\b", f"{title} {url}")
    if match:
        return int(match.group(1))

    match = re.search(r"\b(?:GSA|RFP|IFB|SS|GOV)[^\d]{0,8}\d{1,3}[-_ ](\d{2})\b", title, re.I)
    if match:
        return 2000 + int(match.group(1))

    match = re.search(r"/(20\d{2})/", url)
    if match:
        return int(match.group(1))

    return None


def document_kind(title: str) -> str:
    lowered = title.lower()
    if "signed contract" in lowered or "contract" in lowered:
        return "contract"
    if "award" in lowered:
        return "award"
    if "bid status" in lowered:
        return "bid_status"
    if "amendment" in lowered:
        return "amendment"
    if "question" in lowered or "response" in lowered:
        return "questions_and_responses"
    if "cancelled" in lowered or "canceled" in lowered:
        return "cancellation"
    if "stay of procurement" in lowered:
        return "stay_of_procurement"
    if "request for proposal" in lowered or "rfp" in lowered:
        return "rfp"
    if "invitation for bid" in lowered or "ifb" in lowered or re.search(r"\bGSA[-_ ]\d+", title, re.I):
        return "ifb"
    return "procurement_document"


def is_procurement_link(title: str, url: str) -> bool:
    haystack = f"{title} {url}".lower()
    keywords = [
        "gsa-",
        "ifb",
        "rfp",
        "bid",
        "award",
        "contract",
        "amendment",
        "notice",
        "procurement",
        "questions",
        "response",
        "wp-gsa-content/uploads",
    ]
    return any(keyword in haystack for keyword in keywords)


@mcp.tool()
async def search_procurement_documents(
    query: str,
    year: Optional[int] = None,
    max_results: int = 10,
) -> str:
    """Search Guam GSA procurement document links by keyword.

    Searches the official Guam General Services Agency Invitation for Bid page
    for procurement records such as IFBs, RFPs, amendments, bid status notices,
    intent-of-award notices, cancellations, and signed contracts.

    Args:
        query: Keyword or phrase to search for, such as "office space", "award",
            "signed contract", "copier", or a solicitation number like "GSA-010-23".
        year: Optional four-digit year to filter results, such as 2026 or 2023.
        max_results: Maximum number of matching links to return, from 1 to 50.
    """
    query = normalize_space(query)
    max_results = min(max(max_results, 1), 50)

    try:
        async with httpx.AsyncClient() as client:
            response = await asyncio.wait_for(
                client.get(
                    GSA_IFB_URL,
                    follow_redirects=True,
                    timeout=httpx.Timeout(10, connect=5),
                ),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
    except (asyncio.TimeoutError, httpx.RequestError) as exc:
        return json.dumps(
            {
                "error": "Could not fetch Guam GSA procurement page.",
                "detail": str(exc),
                "source_url": GSA_IFB_URL,
                "suggestion": "Try again later, or verify that the GSA website is reachable from this environment.",
            },
            indent=2,
        )

    if response.status_code != 200:
        return json.dumps(
            {
                "error": "Could not fetch Guam GSA procurement page.",
                "status_code": response.status_code,
                "source_url": GSA_IFB_URL,
            },
            indent=2,
        )

    parser = LinkExtractor()
    parser.feed(response.text)

    query_terms = [term.lower() for term in query.split() if term]
    records = []
    seen_urls = set()

    for link in parser.links:
        title = normalize_space(link["title"])
        url = urljoin(GSA_IFB_URL, link["url"])
        if url in seen_urls or not is_procurement_link(title, url):
            continue

        record_year = document_year(title, url)
        if year and record_year != year:
            continue

        searchable_text = f"{title} {url}".lower()
        if query_terms and not all(term in searchable_text for term in query_terms):
            continue

        seen_urls.add(url)
        records.append(
            {
                "title": title,
                "kind": document_kind(title),
                "year": record_year,
                "url": url,
            }
        )

    return json.dumps(
        {
            "source": "Guam General Services Agency Invitation for Bid page",
            "source_url": GSA_IFB_URL,
            "query": query,
            "year": year,
            "count": len(records[:max_results]),
            "results": records[:max_results],
            "limitations": [
                "This searches document link titles and URLs on the official page.",
                "It does not read the full text inside linked PDFs yet.",
            ],
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
