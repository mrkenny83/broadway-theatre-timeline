#!/usr/bin/env python3
"""Refresh the Broadway timeline from Broadway Now & Next.
Fail closed: never replace data.json when source parsing is incomplete.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
SOURCE = "https://www.broadwaynowandnext.com/"
MISSING = {"", "—", "–", "-", "NA", "N/A", "TBA", "TBD"}
DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
HEADERS = {"THEATRE", "THEATER", "SHOW", "PREVIEW", "OPENING", "CLOSING", "DARK"}

def parse_date(raw):
    raw = re.sub(r"\s+", "", raw.replace("\u200b", ""))
    if raw.upper() in MISSING:
        return None
    if not DATE.fullmatch(raw):
        raise ValueError(f"Unexpected date: {raw!r}")
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Invalid date: {raw!r}")

def date_like(s):
    s = s.strip()
    return bool(DATE.fullmatch(s)) or s.upper() in MISSING

def theatre_name(s, names):
    value = " ".join(s.split()).casefold()
    for name in sorted(names, key=len, reverse=True):
        n = name.casefold()
        if value == n or value.startswith(n + " ") or value.startswith(n + "|"):
            return name
    return None

def from_tables(soup, names):
    rows = {n: [] for n in names}
    seen = set()
    for table in soup.find_all("table"):
        heading = " ".join(table.stripped_strings).lower()[:800]
        if not all(word in heading for word in ("preview", "opening", "closing")):
            continue
        theatre = None
        for tr in table.select("tr"):
            cells = tr.find_all(["td", "th"], recursive=False)
            if len(cells) < 4:
                continue
            vals = [" ".join(c.stripped_strings) for c in cells]
            if len(vals) >= 5:
                found = theatre_name(vals[0], names)
                if found:
                    theatre = found
                    seen.add(found)
            if not theatre or not all(date_like(x) for x in vals[-3:]):
                continue
            title = vals[-4].strip()
            if title and title.upper() not in HEADERS:
                rows[theatre].append({"title": title, "previews": parse_date(vals[-3]),
                                      "opening": parse_date(vals[-2]), "closing": parse_date(vals[-1])})
    return rows, seen

def from_text(soup, names):
    tokens = [" ".join(t.split()) for t in soup.stripped_strings]
    start = next((i for i,t in enumerate(tokens)
                  if "Current & Upcoming Broadway Shows" in t), 0)
    tokens = tokens[start:]
    rows = {n: [] for n in names}
    seen = set()
    theatre = None
    i = 0
    while i < len(tokens):
        word = tokens[i]
        found = theatre_name(word, names)
        if found and (word.casefold() == found.casefold() or re.search(r"\b\d{2,4}\s+[WE]\b", word)):
            theatre = found
            seen.add(found)
            i += 1
            continue
        if theatre and ("Upcoming shows that haven" in word or "announced their theatre yet" in word):
            break
        if theatre and i+3 < len(tokens) and all(date_like(x) for x in tokens[i+1:i+4]):
            if word.upper() not in HEADERS and not re.match(r"^\d+\s+", word):
                rows[theatre].append({"title": word, "previews": parse_date(tokens[i+1]),
                                      "opening": parse_date(tokens[i+2]), "closing": parse_date(tokens[i+3])})
                i += 4
                continue
        i += 1
    return rows, seen

def main():
    original = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    names = [t["name"] for t in original["theatres"]]
    r = requests.get(SOURCE, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (compatible; BroadwayTimeline/1.0; once-daily refresh)",
        "Accept": "text/html,application/xhtml+xml"
    })
    r.raise_for_status()
    if len(r.text) < 2000:
        raise ValueError("Unexpectedly short source response")
    soup = BeautifulSoup(r.text, "html.parser")
    for node in soup(["script", "style", "nav", "footer"]):
        node.decompose()
    rows, seen = from_tables(soup, names)
    if len(seen) < 39 or sum(len(v) for v in rows.values()) < 40:
        rows, seen = from_text(soup, names)
    for n in names:
        unique = {}
        for show in rows[n]:
            if show["previews"] or show["opening"]:
                unique[(show["title"], show["previews"], show["opening"])] = show
        rows[n] = list(unique.values())
    count = sum(len(v) for v in rows.values())
    if len(seen) < 39 or count < 40:
        raise ValueError(f"Rejected incomplete scrape: {len(seen)} theatres, {count} shows")
    updated = {
        "source": SOURCE,
        "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "snapshot": "Automatically refreshed from Broadway Now & Next.",
        "theatres": [{"name": t["name"], "address": t.get("address", ""),
                      "shows": rows[t["name"]]} for t in original["theatres"]]
    }
    (ROOT / "data.json").write_text(json.dumps(updated, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Validated {len(names)} theatres and {count} shows")

if __name__ == "__main__":
    main()
