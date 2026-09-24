from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import BASE_URL, LOCATIONS_PATH


def _clean(text: str) -> str:
    return " ".join(text.split())


def _detail_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.select('a[href*="/communities/"]'):
        href = urljoin(page_url, tag.get("href", ""))
        if href.rstrip("/") != f"{BASE_URL}/communities" and href not in links:
            links.append(href)
    return links


def _parse_detail(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    name = _clean((soup.find("h1") or soup.find("h2")).get_text(" ", strip=True))
    address_match = re.search(
        r"ADDRESS\s*\n([^\n]+)\s*\n([^,\n]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)",
        text,
        re.I,
    )
    if not address_match:
        raise ValueError(f"Could not parse address from {url}")
    offerings = [_clean(tag.get_text(" ", strip=True)) for tag in soup.select("dd .badge")]
    if not offerings:
        care_section = re.search(r"CARE OFFERINGS\s*\n(.*?)(?:\nADMINISTRATOR|\nPHONE|$)", text, re.I | re.S)
        if care_section:
            offerings = [_clean(x) for x in care_section.group(1).split("\n") if _clean(x)]
    return {
        "name": name,
        "street": _clean(address_match.group(1)),
        "city": _clean(address_match.group(2)),
        "state": address_match.group(3).upper(),
        "zip": address_match.group(4),
        "care_offerings": offerings,
        "source_url": url,
    }


def scrape_locations() -> list[dict]:
    session = requests.Session()
    all_links: list[str] = []
    page = 1
    while True:
        page_url = f"{BASE_URL}/communities?page={page}"
        response = session.get(page_url, timeout=30)
        response.raise_for_status()
        links = _detail_links(response.text, page_url)
        new_links = [link for link in links if link not in all_links]
        if not new_links:
            break
        all_links.extend(new_links)
        page += 1
    locations = []
    for url in all_links:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        locations.append(_parse_detail(response.text, url))
    LOCATIONS_PATH.write_text(json.dumps(locations, indent=2), encoding="utf-8")
    return locations


if __name__ == "__main__":
    found = scrape_locations()
    print(f"Scraped {len(found)} communities into {LOCATIONS_PATH}")
