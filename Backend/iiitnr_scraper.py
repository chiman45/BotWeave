#!/usr/bin/env python3
"""
IIIT Naya Raipur Website Scraper
=================================
Crawls the entire iiitnr.ac.in website and saves clean, structured data
to a JSON file that can be uploaded to the BotSetu RAG knowledge base.

Each JSON entry contains:
  - url        : the real page URL the bot can cite
  - title      : page title
  - section    : breadcrumb / section path (e.g. "Academics > Faculty")
  - content    : clean main-body text (navigation & footer stripped)
  - key_links  : important links found on the page (downloads, sub-pages)

Usage:
  python iiitnr_scraper.py                         # scrape with defaults
  python iiitnr_scraper.py --max-pages 600         # scrape up to 600 pages
  python iiitnr_scraper.py --output my_data.json   # custom output file
  python iiitnr_scraper.py --delay 1.0             # polite 1-second delay

Requirements:
  pip install requests beautifulsoup4 lxml
"""

import argparse
import json
import logging
import re
import time
import warnings
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings — the IIIT-NR cert chain may not verify on Windows
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL    = "https://www.iiitnr.ac.in"
OUTPUT_FILE = "iiitnr_scraped.json"
MAX_PAGES   = 400
DELAY       = 0.8   # seconds between requests — be polite

ALLOWED_DOMAINS = {"www.iiitnr.ac.in", "iiitnr.ac.in"}

# URL patterns to skip entirely
SKIP_URL_RE = re.compile(
    r"(\.(pdf|doc|docx|ppt|pptx|xls|xlsx|zip|rar|gz|tar|jpg|jpeg|png|gif|svg|mp4|mp3|wav|ico|css|js|woff|woff2|ttf))"
    r"|(#)"
    r"|(javascript:)"
    r"|(mailto:)"
    r"|(tel:)"
    r"|(/user/)"
    r"|(/search)"
    r"|(/print/)"
    r"|(/node/add)"
    r"|(/admin)",
    re.IGNORECASE,
)

# HTML elements that are pure navigation / chrome — strip from every page
NOISE_TAGS = {"script", "style", "noscript", "iframe", "form"}

# CSS selectors for "navigation chrome" blocks that repeat on every page
NOISE_SELECTORS = [
    "header", "nav", "footer",
    "#header", "#footer", "#navigation",
    ".site-header", ".site-footer",
    ".region-header", ".region-footer",
    ".main-menu", ".secondary-menu", ".menu-block-wrapper",
    ".region-navigation", ".region-sidebar-first", ".region-sidebar-second",
    "#block-menu-block-1", "#block-menu-block-2",
    ".breadcrumb",
    ".feed-icons",
    ".links.inline",
    ".add-or-login-to-post-comments",
    "#comments",
    # The 'Skip to main content / screen reader' link at the very top
    ".skip-link",
    ".element-invisible",
    ".region-preface",
    "#block-search-form",
    ".search-form",
    "#sliding-popup",       # cookie consent
    ".eu-cookie-compliance-banner",
]

# Selectors tried IN ORDER for the main content block (first match wins)
MAIN_CONTENT_SELECTORS = [
    "#block-system-main",          # Drupal default main block
    "div[role='main']",
    "main",
    "#main-content",
    "#content",
    ".region-content",
    ".main-container",
    "article",
    ".view-content",
    ".field-items",
    "body",                        # absolute fallback
]

# Footer contact block that repeats on every IIIT-NR page — strip it from content
FOOTER_MARKERS = [
    "Contact IIIT",
    "Contact IIIT\u2013Naya Raipur",   # en-dash variant
    "Plot No. 7, Sector 24",
    "Sitemap Terms",
    "Back to Top",
]

# Breadcrumb separator text that precedes actual content on IIIT-NR pages
BREADCRUMB_MARKER = "Home >"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("iiitnr_scraper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise_url(url: str) -> str:
    """Strip fragment, normalise scheme+host, remove trailing slash."""
    p = urlparse(url)
    # Force https
    scheme = "https"
    # Strip www for dedup (treat iiitnr.ac.in == www.iiitnr.ac.in)
    netloc = p.netloc.lower().replace("://", "")
    path   = p.path.rstrip("/") or "/"
    # Drop query + fragment for dedup (keep query only for specific paths that need it)
    return urlunparse((scheme, p.netloc.lower(), path, "", "", ""))


def should_skip_url(url: str) -> bool:
    return bool(SKIP_URL_RE.search(url))


def is_allowed_domain(url: str) -> bool:
    return urlparse(url).netloc.lower() in ALLOWED_DOMAINS


def strip_footer(text: str) -> str:
    """Remove the repeated contact/footer block from page text."""
    for marker in FOOTER_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
    return text.strip()


def strip_nav_prefix(text: str) -> str:
    """Strip navigation menu text that precedes 'Home >' on IIIT-NR pages."""
    idx = text.find(BREADCRUMB_MARKER)
    if idx != -1:
        # Keep content after "Home > [breadcrumb path]" intro
        after = text[idx + len(BREADCRUMB_MARKER):].strip()
        # If it starts with a breadcrumb path (e.g. "Academics >  Faculty" space)
        # skip another ">" separated segment if very short
        return after
    return text


def clean_text(text: str) -> str:
    """Collapse whitespace and remove non-printable artifacts."""
    text = text.replace("ï»¿", "")           # UTF-8 BOM artifact
    text = re.sub(r"[ \t]{2,}", " ", text)   # collapse horizontal whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)   # max 2 blank lines
    text = text.strip()
    return text


def get_breadcrumb(soup: BeautifulSoup) -> str:
    """Try to extract a breadcrumb string like 'Academics > Faculty Profile'."""
    bc = soup.find(class_="breadcrumb") or soup.find("nav", {"aria-label": re.compile("breadcrumb", re.I)})
    if bc:
        parts = [a.get_text(strip=True) for a in bc.find_all("a")]
        # Last item is usually the current page title
        current = bc.find("li", class_="active") or bc.find("span", class_="active")
        if current:
            parts.append(current.get_text(strip=True))
        return " > ".join(p for p in parts if p and p.lower() != "home")
    return ""


def extract_key_links(main_node: BeautifulSoup, page_url: str) -> list:
    """
    Extract links worth preserving — downloads, important sub-pages, etc.
    Returns list of {text, url} dicts with the REAL absolute URL.
    """
    seen = set()
    links = []
    for a in main_node.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        text = a.get_text(strip=True)
        if not text or len(text) < 3 or len(text) > 120:
            continue
        # Skip nav-menu-style very short labels
        if text.lower() in {"home", "read more", "more", "click here", "here", "login", "back"}:
            continue
        full_url = urljoin(page_url, href)
        norm = normalise_url(full_url)
        if norm in seen:
            continue
        seen.add(norm)
        links.append({"text": text, "url": full_url})
        if len(links) >= 30:
            break
    return links


def extract_page(html: str, url: str) -> dict | None:
    """
    Parse a page's HTML and return a structured dict, or None if there's
    no meaningful content.
    """
    soup = BeautifulSoup(html, "lxml")

    # ── Remove HTML comments ────────────────────────────────────────────────
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # ── Remove noisy tags completely ────────────────────────────────────────
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()

    # ── Page title ──────────────────────────────────────────────────────────
    title_tag  = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""
    # Strip " | IIIT NAYA RAIPUR" suffix for cleaner titles
    page_title = re.sub(r"\s*\|\s*IIIT NAYA RAIPUR$", "", page_title, flags=re.I).strip()

    # ── Breadcrumb / section path ───────────────────────────────────────────
    section = get_breadcrumb(soup)

    # ── Remove navigation chrome BEFORE extracting text ────────────────────
    for sel in NOISE_SELECTORS:
        for elem in soup.select(sel):
            elem.decompose()

    # ── Find main content area ───────────────────────────────────────────────
    main_node = None
    for sel in MAIN_CONTENT_SELECTORS:
        main_node = soup.select_one(sel)
        if main_node:
            break
    if not main_node:
        return None

    # ── Extract key links BEFORE stripping tags ─────────────────────────────
    key_links = extract_key_links(main_node, url)

    # ── Get text ─────────────────────────────────────────────────────────────
    # Use newlines on block elements for readability
    for tag in main_node.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "tr", "div"]):
        tag.insert_before("\n")

    content = main_node.get_text(separator=" ")
    content = strip_nav_prefix(content)
    content = strip_footer(content)
    content = clean_text(content)

    # Skip pages with no meaningful content
    if len(content) < 80:
        return None

    return {
        "url":       url,
        "title":     page_title,
        "section":   section,
        "content":   content,
        "key_links": key_links,
    }


# ── Crawler ───────────────────────────────────────────────────────────────────

def crawl(start_url: str = BASE_URL, max_pages: int = MAX_PAGES, delay: float = DELAY) -> list:
    visited: set[str]  = set()
    queue:   deque[str] = deque([normalise_url(start_url)])
    results: list[dict] = []

    session = requests.Session()
    session.headers.update({
        "User-Agent":      "Mozilla/5.0 (compatible; BotSetuCrawler/1.0; educational bot)",
        "Accept":          "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection":      "keep-alive",
    })

    while queue and len(visited) < max_pages:
        url = queue.popleft()

        if url in visited:
            continue
        if should_skip_url(url):
            continue
        if not is_allowed_domain(url):
            continue

        visited.add(url)
        log.info(f"[{len(visited):>3}/{max_pages}] {url}")

        try:
            resp = session.get(url, timeout=15, allow_redirects=True, verify=False)

            # Follow redirects but update final URL
            final_url = resp.url
            final_norm = normalise_url(final_url)
            if final_norm != url:
                if final_norm in visited:
                    continue
                visited.add(final_norm)

            if resp.status_code != 200:
                log.warning(f"  HTTP {resp.status_code} — skipping")
                continue

            ct = resp.headers.get("Content-Type", "")
            if "html" not in ct:
                log.debug(f"  Not HTML ({ct}) — skipping")
                continue

            # ── Parse ─────────────────────────────────────────────────────
            page_data = extract_page(resp.text, final_url)

            if page_data:
                results.append(page_data)
                log.info(f"  ✓ [section={page_data['section']!r}] {len(page_data['content'])} chars, {len(page_data['key_links'])} links")
            else:
                log.debug(f"  ✗ No usable content")

            # ── Discover new links ─────────────────────────────────────────
            raw_soup = BeautifulSoup(resp.text, "lxml")
            for a_tag in raw_soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                if not href:
                    continue
                full = urljoin(final_url, href)
                norm = normalise_url(full)
                if (
                    norm not in visited
                    and is_allowed_domain(full)
                    and not should_skip_url(norm)
                ):
                    queue.append(norm)

            time.sleep(delay)

        except requests.exceptions.Timeout:
            log.warning(f"  Timeout — skipping {url}")
        except requests.exceptions.ConnectionError as e:
            log.warning(f"  Connection error — {e}")
        except Exception as e:
            log.error(f"  Unexpected error: {e}", exc_info=True)

    log.info(f"\n{'='*60}")
    log.info(f"Crawl complete: {len(results)} pages saved / {len(visited)} URLs visited")
    log.info(f"{'='*60}\n")
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape IIIT Naya Raipur website for RAG knowledge base",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--start",     default=BASE_URL,    help="Starting URL")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES, help="Max pages to crawl")
    parser.add_argument("--delay",     type=float, default=DELAY,   help="Delay between requests (s)")
    parser.add_argument("--output",    default=OUTPUT_FILE, help="Output JSON file path")
    args = parser.parse_args()

    log.info(f"Starting IIIT-NR scraper")
    log.info(f"  Start URL : {args.start}")
    log.info(f"  Max pages : {args.max_pages}")
    log.info(f"  Delay     : {args.delay}s")
    log.info(f"  Output    : {args.output}")
    log.info("")

    pages = crawl(args.start, args.max_pages, args.delay)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)

    log.info(f"Saved {len(pages)} pages → {args.output}")
    print(f"\nDone! {len(pages)} pages saved to {args.output}")
    print(f"Upload this file to the BotSetu dashboard to build the knowledge base.")


if __name__ == "__main__":
    main()
