"""Lucienne's inspection toolkit: page fetch + SEO signal extraction,
robots/sitemap checks, and Core Web Vitals via the PageSpeed Insights API.

Pure functions returning JSON-serializable dicts, so the Bedrock agent can
call them as tools and the results stay inspectable in logs.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (compatible; LucienneBot/1.0; +https://hero-apps.com/lucienne)"
)
MAX_BYTES = 1_500_000
TIMEOUT = 20


def _get(url: str, max_bytes: int = MAX_BYTES) -> tuple[bytes, dict, list[str], float, int]:
    """Fetch a URL following redirects. Returns (body, headers, redirect_chain, ttfb_s, status)."""
    chain: list[str] = []

    class _Redirects(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            chain.append(f"{code} -> {newurl}")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(_Redirects)
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Encoding": "identity",
    })
    start = time.monotonic()
    with opener.open(req, timeout=TIMEOUT) as resp:
        first = resp.read(1)
        ttfb = time.monotonic() - start
        body = first + resp.read(max_bytes)
        headers = {k.lower(): v for k, v in resp.headers.items()}
        status = resp.status
    return body, headers, chain, ttfb, status


def _normalize_url(url: str) -> str:
    url = url.strip().strip('<>"\'')
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def _text_between(html: str, pattern: str) -> str | None:
    m = re.search(pattern, html, re.I | re.S)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()


def _attr_of_tags(html: str, tag_pattern: str, attr: str) -> list[str]:
    out = []
    for tag in re.findall(tag_pattern, html, re.I | re.S):
        m = re.search(attr + r"""\s*=\s*["']([^"']*)["']""", tag, re.I)
        if m:
            out.append(m.group(1).strip())
    return out


def inspect_page(url: str) -> dict:
    """Fetch one page and extract the technical SEO signals that matter."""
    url = _normalize_url(url)
    try:
        body, headers, chain, ttfb, status = _get(url)
    except Exception as e:  # noqa: BLE001 - report fetch failures to the agent
        return {"url": url, "error": f"fetch failed: {e.__class__.__name__}: {e}"}

    html = body.decode("utf-8", errors="replace")
    lower = html.lower()

    title = _text_between(html, r"<title[^>]*>(.*?)</title>")
    metas = re.findall(r"<meta\b[^>]*>", html, re.I)

    def meta_content(name: str, key: str = "name") -> str | None:
        for m in metas:
            if re.search(key + r"""\s*=\s*["']""" + re.escape(name) + r"""["']""", m, re.I):
                c = re.search(r"""content\s*=\s*["']([^"']*)["']""", m, re.I)
                if c:
                    return c.group(1).strip()
        return None

    links = re.findall(r"<link\b[^>]*>", html, re.I)

    def link_href(rel: str) -> list[str]:
        out = []
        for l in links:
            if re.search(r"""rel\s*=\s*["']""" + rel + r"""["']""", l, re.I):
                h = re.search(r"""href\s*=\s*["']([^"']*)["']""", l, re.I)
                if h:
                    out.append(h.group(1))
        return out

    imgs = re.findall(r"<img\b[^>]*>", html, re.I)
    imgs_missing_alt = [
        i for i in imgs
        if not re.search(r"""\balt\s*=\s*["'][^"']+["']""", i, re.I)
    ]

    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    h1s = [re.sub(r"<[^>]+>|\s+", " ", h).strip()[:120] for h in h1s]

    jsonld_types: list[str] = []
    for block in re.findall(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.I | re.S,
    ):
        try:
            data = json.loads(block)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    t = item.get("@type")
                    if isinstance(t, list):
                        jsonld_types += [str(x) for x in t]
                    elif t:
                        jsonld_types.append(str(t))
        except Exception:  # noqa: BLE001
            jsonld_types.append("(unparseable JSON-LD block)")

    text_only = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S)
    text_only = re.sub(r"<[^>]+>", " ", text_only)
    words = len(re.findall(r"\w+", text_only))

    return {
        "url": url,
        "status": status,
        "redirect_chain": chain,
        "https": url.startswith("https://"),
        "ttfb_seconds": round(ttfb, 2),
        "page_bytes": len(body),
        "truncated": len(body) > MAX_BYTES,
        "content_encoding": headers.get("content-encoding", "none"),
        "cache_control": headers.get("cache-control"),
        "x_robots_tag": headers.get("x-robots-tag"),
        "title": title,
        "title_length": len(title) if title else 0,
        "meta_description": meta_content("description"),
        "meta_robots": meta_content("robots"),
        "viewport": meta_content("viewport"),
        "canonical": link_href("canonical"),
        "hreflang_count": len([l for l in links if "hreflang" in l.lower()]),
        "favicon": bool(link_href("(?:shortcut )?icon")),
        "h1_count": len(h1s),
        "h1s": h1s[:5],
        "img_count": len(imgs),
        "imgs_missing_alt": len(imgs_missing_alt),
        "og_title": meta_content("og:title", key="property"),
        "og_description": meta_content("og:description", key="property"),
        "og_image": meta_content("og:image", key="property"),
        "twitter_card": meta_content("twitter:card"),
        "jsonld_types": jsonld_types[:10],
        "word_count": words,
        "has_noindex": bool(
            (meta_content("robots") or "").lower().find("noindex") >= 0
            or (headers.get("x-robots-tag") or "").lower().find("noindex") >= 0
        ),
        "lang_attr": _text_between(html, r"<html[^>]*\blang\s*=\s*[\"']([^\"']+)[\"']"),
    }


def check_robots_sitemap(url: str) -> dict:
    """Check robots.txt and sitemap presence for the site of the given URL."""
    url = _normalize_url(url)
    parts = urllib.parse.urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    out: dict = {"site": root}

    try:
        body, _, _, _, status = _get(root + "/robots.txt", max_bytes=100_000)
        txt = body.decode("utf-8", errors="replace")
        out["robots_txt"] = {
            "status": status,
            "disallow_all": bool(re.search(r"^\s*Disallow:\s*/\s*$", txt, re.M)),
            "sitemaps": re.findall(r"(?im)^\s*Sitemap:\s*(\S+)", txt),
            "first_lines": txt.splitlines()[:15],
        }
    except Exception as e:  # noqa: BLE001
        out["robots_txt"] = {"error": str(e)}

    sitemap_urls = (out.get("robots_txt") or {}).get("sitemaps") or [root + "/sitemap.xml"]
    try:
        body, _, _, _, status = _get(sitemap_urls[0], max_bytes=200_000)
        xml = body.decode("utf-8", errors="replace")
        out["sitemap"] = {
            "url": sitemap_urls[0],
            "status": status,
            "url_count": xml.count("<loc>"),
            "is_index": "<sitemapindex" in xml,
        }
    except Exception as e:  # noqa: BLE001
        out["sitemap"] = {"url": sitemap_urls[0], "error": str(e)}

    return out


def core_web_vitals(url: str, strategy: str = "mobile") -> dict:
    """Run Google PageSpeed Insights for lab + field Core Web Vitals."""
    url = _normalize_url(url)
    api = (
        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?"
        + urllib.parse.urlencode({
            "url": url,
            "strategy": strategy,
            "category": "performance",
        })
    )
    key = os.environ.get("PSI_API_KEY")
    if key:
        api += "&key=" + key
    req = urllib.request.Request(api, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=110) as resp:
            data = json.loads(resp.read())
    except Exception as e:  # noqa: BLE001
        return {"url": url, "error": f"PSI failed: {e}"}

    out: dict = {"url": url, "strategy": strategy}
    lh = data.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    cats = lh.get("categories", {})
    if cats.get("performance", {}).get("score") is not None:
        out["performance_score"] = round(cats["performance"]["score"] * 100)
    for key_, audit in [
        ("lcp_lab", "largest-contentful-paint"),
        ("cls_lab", "cumulative-layout-shift"),
        ("tbt_lab", "total-blocking-time"),
        ("fcp_lab", "first-contentful-paint"),
        ("speed_index_lab", "speed-index"),
    ]:
        a = audits.get(audit, {})
        if a.get("displayValue"):
            out[key_] = a["displayValue"]

    field = data.get("loadingExperience", {}).get("metrics", {})
    fields = {}
    for name, metric in [
        ("lcp_field_ms", "LARGEST_CONTENTFUL_PAINT_MS"),
        ("inp_field_ms", "INTERACTION_TO_NEXT_PAINT"),
        ("cls_field", "CUMULATIVE_LAYOUT_SHIFT_SCORE"),
    ]:
        m = field.get(metric)
        if m:
            fields[name] = {"p75": m.get("percentile"), "category": m.get("category")}
    if fields:
        out["field_data_p75"] = fields
    else:
        out["field_data_p75"] = "no CrUX field data for this URL (low traffic)"
    return out


def _sitemap_locs(url: str, depth: int = 0) -> list[str]:
    body, _, _, _, _ = _get(url, max_bytes=2_000_000)
    xml = body.decode("utf-8", errors="replace")
    locs = [l.strip() for l in re.findall(r"<loc>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</loc>", xml, re.S)]
    if "<sitemapindex" in xml and depth == 0:
        pages: list[str] = []
        for child in locs[:5]:  # page sitemaps first is the common order; enough for a small business
            try:
                pages += _sitemap_locs(child, 1)
            except Exception:  # noqa: BLE001
                continue
        return pages
    return locs


def _suggest(query: str, lang: str) -> list[str]:
    api = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
        {"client": "firefox", "hl": lang, "ie": "utf-8", "oe": "utf-8", "q": query})
    body, _, _, _, _ = _get(api, max_bytes=50_000)
    data = json.loads(body.decode("utf-8", errors="replace"))
    return [s for s in data[1] if s.strip().lower() != query.strip().lower()]


def content_ideas(url: str, topics: list[str], lang: str = "en") -> dict:
    """What the site already covers (sitemap pages) next to what people type into
    Google about its topics (Autocomplete), so content advice targets real gaps."""
    from concurrent.futures import ThreadPoolExecutor

    url = _normalize_url(url)
    parts = urllib.parse.urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    out: dict = {"site": root}

    sitemaps = [root + "/sitemap.xml", root + "/sitemap_index.xml"]
    try:
        robots = _get(root + "/robots.txt", max_bytes=100_000)[0].decode("utf-8", errors="replace")
        sitemaps = re.findall(r"(?im)^\s*Sitemap:\s*(\S+)", robots) + sitemaps
    except Exception:  # noqa: BLE001
        pass
    for sm in sitemaps:
        try:
            locs = list(dict.fromkeys(_sitemap_locs(sm)))
        except Exception:  # noqa: BLE001
            continue
        if locs:
            paths = [urllib.parse.urlsplit(l).path or "/" for l in locs]
            out["existing_pages"] = {"sitemap": sm, "count": len(paths), "paths": paths[:150]}
            break
    else:
        out["existing_pages"] = {"error": "no readable sitemap; existing coverage unknown"}

    seeds = [t.strip() for t in topics if t.strip()][:4]
    queries = [q for s in seeds for q in (s, s + " ")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda q: (q, _safe(lambda: _suggest(q, lang))), queries))
    searches: dict[str, list[str]] = {}
    for q, res in results:
        if isinstance(res, list):
            seen = searches.setdefault(q.strip(), [])
            seen += [s for s in res if s not in seen]
    out["google_autocomplete"] = searches or {"error": "autocomplete unavailable"}
    out["note"] = "Autocomplete shows phrases people really search, not their volume."
    return out


def _safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
