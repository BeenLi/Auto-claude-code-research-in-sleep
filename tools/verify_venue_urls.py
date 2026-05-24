#!/usr/bin/env python3
"""Verify documented research-lit venue URLs for maintenance.

The checker expands each VenuePattern for the current and previous year, fetches
the resulting URLs, and reports status_code, redirect_target, and
venue_relevant. It is intentionally non-blocking: live conference sites move,
block bots, and publish future-year pages late, so this script returns success
after reporting what it observed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import socket
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterable


DEFAULT_TIMEOUT_SECONDS = 12
READ_BYTES = 65536


@dataclass(frozen=True)
class VenuePattern:
    venue: str
    kind: str
    pattern: str
    relevance_terms: tuple[str, ...]


VENUE_PATTERNS: tuple[VenuePattern, ...] = (
    VenuePattern("ASPLOS", "dblp-part-1", "https://dblp.org/db/conf/asplos/asplos{YYYY}-1.html", ("asplos",)),
    VenuePattern("ASPLOS", "dblp-part-2", "https://dblp.org/db/conf/asplos/asplos{YYYY}-2.html", ("asplos",)),
    VenuePattern(
        "ASPLOS",
        "official",
        "https://www.asplos-conference.org/asplos{YYYY}/",
        ("asplos",),
    ),
    VenuePattern("ISCA", "dblp", "https://dblp.org/db/conf/isca/isca{YYYY}.html", ("isca",)),
    VenuePattern("ISCA", "official", "https://iscaconf.org/isca{YYYY}/", ("isca",)),
    VenuePattern("MICRO", "dblp", "https://dblp.org/db/conf/micro/micro{YYYY}.html", ("micro",)),
    VenuePattern("MICRO", "official", "https://microarch.org/micro{EDITION}/", ("micro",)),
    VenuePattern("HPCA", "dblp", "https://dblp.org/db/conf/hpca/hpca{YYYY}.html", ("hpca",)),
    VenuePattern("HPCA", "official", "https://hpca-conf.org/{YYYY}/", ("hpca",)),
    VenuePattern("SOSP", "dblp", "https://dblp.org/db/conf/sosp/sosp{YYYY}.html", ("sosp",)),
    VenuePattern(
        "SOSP",
        "official",
        "https://sigops.org/s/conferences/sosp/{YYYY}/",
        ("sosp", "sigops"),
    ),
    VenuePattern("OSDI", "dblp", "https://dblp.org/db/conf/osdi/osdi{YYYY}.html", ("osdi",)),
    VenuePattern(
        "OSDI",
        "official",
        "https://www.usenix.org/conference/osdi{YY}/technical-sessions",
        ("osdi", "usenix"),
    ),
    VenuePattern("NSDI", "dblp", "https://dblp.org/db/conf/nsdi/nsdi{YYYY}.html", ("nsdi",)),
    VenuePattern(
        "NSDI",
        "official",
        "https://www.usenix.org/conference/nsdi{YY}/technical-sessions",
        ("nsdi", "usenix"),
    ),
    VenuePattern(
        "USENIX ATC",
        "dblp",
        "https://dblp.org/db/conf/usenix/usenix{YYYY}.html",
        ("usenix",),
    ),
    VenuePattern(
        "USENIX ATC",
        "official",
        "https://www.usenix.org/conference/atc{YY}/technical-sessions",
        ("atc", "usenix"),
    ),
    VenuePattern(
        "SIGCOMM",
        "dblp",
        "https://dblp.org/db/conf/sigcomm/sigcomm{YYYY}.html",
        ("sigcomm",),
    ),
    VenuePattern(
        "SIGCOMM",
        "official",
        "https://conferences.sigcomm.org/sigcomm/{YYYY}/",
        ("sigcomm",),
    ),
    VenuePattern(
        "EuroSys",
        "dblp",
        "https://dblp.org/db/conf/eurosys/eurosys{YYYY}.html",
        ("eurosys",),
    ),
    VenuePattern("EuroSys", "official", "https://www.eurosys.org/", ("eurosys",)),
    VenuePattern("MLSys", "dblp", "https://dblp.org/db/conf/mlsys/mlsys{YYYY}.html", ("mlsys",)),
    VenuePattern("MLSys", "official", "https://mlsys.org/virtual/{YYYY}/papers.html", ("mlsys",)),
)


@dataclass(frozen=True)
class CheckResult:
    venue: str
    kind: str
    year: int
    url: str
    status_code: str
    redirect_target: str
    venue_relevant: bool
    error: str


def micro_edition(year: int) -> int:
    """MICRO edition number for a given calendar year.

    Anchored at MICRO 57 = 2024 and MICRO 58 = 2025; assumes the symposium
    never skips a year. If MICRO renumbers or skips, replace this linear
    formula with an explicit `{year: edition}` mapping.
    """

    return year - 1967


def render(pattern: str, year: int) -> str:
    return pattern.format(YYYY=year, YY=str(year)[-2:], EDITION=micro_edition(year))


def appears_relevant(url: str, body: bytes, terms: Iterable[str]) -> bool:
    haystack = url.lower() + "\n" + body.decode("utf-8", errors="ignore").lower()
    return any(term.lower() in haystack for term in terms)


def fetch_url(url: str, timeout: float, insecure: bool) -> tuple[str, str, bytes, str]:
    context = ssl._create_unverified_context() if insecure else None
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ARIS research-lit venue verifier/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            status_code = str(response.getcode())
            final_url = response.geturl()
            body = response.read(READ_BYTES)
            return status_code, final_url, body, ""
    except urllib.error.HTTPError as exc:
        body = exc.read(READ_BYTES)
        final_url = exc.geturl()
        return str(exc.code), final_url, body, ""
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        return "ERROR", "", b"", str(exc.reason if isinstance(exc, urllib.error.URLError) else exc)
    except Exception as exc:  # non-blocking maintenance tool; swallow stragglers like SSLError/RemoteDisconnected
        return "ERROR", "", b"", f"{type(exc).__name__}: {exc}"


def check_pattern(pattern: VenuePattern, year: int, timeout: float, insecure: bool) -> CheckResult:
    url = render(pattern.pattern, year)
    status_code, final_url, body, error = fetch_url(url, timeout=timeout, insecure=insecure)
    redirect_target = final_url if final_url and final_url != url else ""
    return CheckResult(
        venue=pattern.venue,
        kind=pattern.kind,
        year=year,
        url=url,
        status_code=status_code,
        redirect_target=redirect_target,
        venue_relevant=appears_relevant(final_url or url, body, pattern.relevance_terms),
        error=error,
    )


def iter_years(base_year: int) -> tuple[int, int]:
    return (base_year, base_year - 1)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year",
        type=int,
        default=dt.date.today().year,
        help="base year to verify; current and previous year are checked",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--jobs", type=int, default=4, help="parallel URL checks")
    parser.add_argument("--insecure", action="store_true", help="skip TLS certificate verification")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    print("venue\tkind\tyear\tstatus_code\tredirect_target\tvenue_relevant\turl\terror")
    jobs = max(1, args.jobs)
    checks: list[tuple[VenuePattern, int]] = []
    seen_urls: set[tuple[str, str, str]] = set()
    for year in iter_years(args.year):
        for pattern in VENUE_PATTERNS:
            key = (pattern.venue, pattern.kind, render(pattern.pattern, year))
            if key in seen_urls:
                continue
            seen_urls.add(key)
            checks.append((pattern, year))
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = [
            executor.submit(check_pattern, pattern, year=year, timeout=args.timeout, insecure=args.insecure)
            for pattern, year in checks
        ]
        for future in futures:
            result = future.result()
            print(
                "\t".join(
                    [
                        result.venue,
                        result.kind,
                        str(result.year),
                        result.status_code,
                        result.redirect_target,
                        str(result.venue_relevant).lower(),
                        result.url,
                        result.error.replace("\t", " "),
                    ]
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
