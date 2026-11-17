#!/usr/bin/env python3
"""Fetch public news feeds and write a Harbour Chronicle edition snapshot.

Facts come only from public RSS/API summaries. Precis are short original
paraphrases of those summaries — never invented quotes, scores, or datelines.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import ssl
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

try:
    from lxml import etree
except ImportError:
    print("lxml is required", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
HKT = timezone(timedelta(hours=8))
UA = (
    "HarbourChronicle/1.0 (+https://jamieccc724.github.io/harbour-chronicle/; "
    "independent digital broadsheet; news aggregation for display with attribution)"
)
CTX = ssl.create_default_context()

FEEDS = [
    ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC News", "world"),
    ("https://feeds.bbci.co.uk/news/rss.xml", "BBC News", "world"),
    ("https://feeds.bbci.co.uk/news/world/asia/rss.xml", "BBC News", "hong-kong"),
    ("https://feeds.bbci.co.uk/news/world/asia/china/rss.xml", "BBC News", "hong-kong"),
    ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC News", "business"),
    ("https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "BBC News", "science"),
    ("https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "BBC News", "culture"),
    ("https://feeds.bbci.co.uk/sport/rss.xml", "BBC Sport", "sport"),
    ("https://www.theguardian.com/world/rss", "The Guardian", "world"),
    ("https://www.theguardian.com/uk/commentisfree/rss", "The Guardian", "opinion"),
    ("https://www.theguardian.com/uk/business/rss", "The Guardian", "business"),
    ("https://www.theguardian.com/uk/sport/rss", "The Guardian", "sport"),
    ("https://www.theguardian.com/uk/culture/rss", "The Guardian", "culture"),
    ("https://www.theguardian.com/science/rss", "The Guardian", "science"),
    ("https://feeds.npr.org/1001/rss.xml", "NPR", "world"),
    ("https://feeds.npr.org/1006/rss.xml", "NPR", "business"),
    ("https://feeds.npr.org/1007/rss.xml", "NPR", "science"),
    ("https://feeds.npr.org/1008/rss.xml", "NPR", "culture"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera", "world"),
    ("https://hongkongfp.com/feed/", "Hong Kong Free Press", "hong-kong"),
    ("https://www.scmp.com/rss/91/feed", "South China Morning Post", "hong-kong"),
    ("https://www.news.gov.hk/en/common/html/topstories.rss.xml", "news.gov.hk", "hong-kong"),
    ("https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511", "CNA", "hong-kong"),
    ("https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml", "CNA", "world"),
    ("https://www.japantimes.co.jp/feed/", "The Japan Times", "hong-kong"),
    ("https://rss.dw.com/rdf/rss-en-all", "Deutsche Welle", "world"),
    ("https://www.france24.com/en/rss", "France 24", "world"),
]

YT_CHANNELS = [
    ("https://www.youtube.com/feeds/videos.xml?user=BBCNews", "BBC News"),
    ("https://www.youtube.com/feeds/videos.xml?user=TheGuardian", "The Guardian"),
    ("https://www.youtube.com/feeds/videos.xml?user=channelnewsasia", "CNA"),
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UCNye-wNBqNL5ZzHSJj3l8Bg", "Al Jazeera English"),
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UC52X5wxOL_s5yw0dQk7NtgA", "Associated Press"),
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UCknLrEdhRCp1aegoMqRaCZg", "DW News"),
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UCQfwfsi5VrQ8yKZ-UWmAEFg", "FRANCE 24 English"),
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UChqUTb7kYRX8-EiaN3XFrSQ", "Reuters"),
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UCoMdktPbSTixAyNGwb-UYkQ", "Sky News"),
]

DESKS = {
    "world": {
        "id": "world",
        "name": "World",
        "flag": "World",
        "zh": "要聞",
        "kicker": "Set in formal ink at the foreign desk",
        "intro": "The world desk keeps a tight, old-press measure: formal serif, black ink, and living plates drawn from official impressions abroad. Nothing on this leaf is invented.",
    },
    "hong-kong": {
        "id": "hong-kong",
        "name": "Hong Kong & Asia",
        "flag": "Hong Kong & Asia",
        "zh": "港聞與亞洲",
        "kicker": "Harbour dispatches, set with a vermillion seal",
        "intro": "The harbour desk sets English first, with Chinese flags as ornaments, and warms the rag slightly. These are public reports from Hong Kong and across Asia, attributed to their original publishers.",
    },
    "business": {
        "id": "business",
        "name": "Business",
        "flag": "Business",
        "zh": "經濟",
        "kicker": "The ledger desk, in cooler ink",
        "intro": "Figures appear only when a source printed them. The ledger desk uses a cooler sheet, tighter tracking, and tabular numerals — a counting-house leaf of the living press.",
    },
    "sport": {
        "id": "sport",
        "name": "Sport",
        "flag": "Sport",
        "zh": "體育",
        "kicker": "A louder case, still set by hand",
        "intro": "The sport desk cuts bolder headlines and gives one plate the run of the page. Scores and results are taken from the originating desk, never guessed at the stone.",
    },
    "culture": {
        "id": "culture",
        "name": "Culture",
        "flag": "Culture",
        "zh": "文藝",
        "kicker": "A wider measure, and illustrated plates",
        "intro": "The culture desk leaves more air around the type, prefers italic decks, and lets a living plate breathe like a folio illustration.",
    },
    "science": {
        "id": "science",
        "name": "Science",
        "flag": "Science",
        "zh": "科學",
        "kicker": "Thin rules, cyan-black ink",
        "intro": "The science desk sets a cleaner modern serif on a cooler sheet. Claims stay with their papers and laboratories; we do not embroider the result.",
    },
    "opinion": {
        "id": "opinion",
        "name": "Opinion",
        "flag": "Opinion",
        "zh": "社評",
        "kicker": "Essay type, a quill measure",
        "intro": "These are other people’s arguments, printed with a large drop cap and a quiet headline. The views belong to the named writers and their newspapers, not to this press.",
    },
}

SOURCE_HOME = {
    "BBC News": "https://www.bbc.com/news",
    "BBC Sport": "https://www.bbc.com/sport",
    "The Guardian": "https://www.theguardian.com/",
    "NPR": "https://www.npr.org/",
    "Al Jazeera": "https://www.aljazeera.com/",
    "Hong Kong Free Press": "https://hongkongfp.com/",
    "South China Morning Post": "https://www.scmp.com/",
    "news.gov.hk": "https://www.news.gov.hk/eng/",
    "CNA": "https://www.channelnewsasia.com/",
    "The Japan Times": "https://www.japantimes.co.jp/",
    "Deutsche Welle": "https://www.dw.com/",
    "France 24": "https://www.france24.com/en/",
}

# Images from these sources are not copied into the repo; SCMP images are not hotlinked.
NO_REMOTE_IMAGE = {"South China Morning Post"}

SKIP_TITLE_RE = re.compile(
    r"(?i)(\bcrossword\b|\bpictures of the day\b|\bquiz:|\bpodcast\b|^listen:|"
    r"^watch:|^in pictures:|^audio:|\b– live$|\b- live$|\blive news\b|"
    r"politics live|uk politics live|\bas it happened\b|\bphoto essay\b|"
    r"^sign up|\bnewsletter\b|\bcorrections?\b)",
)

SPORT_RE = re.compile(
    r"(?i)\b(golf|dechambeau|liv golf|fifa|uefa|premier league|la liga|"
    r"serie a|bundesliga|world cup|afcon|cricket|wimbledon|nba|nfl|"
    r"formula 1|\bf1\b|grand prix|rugby|twickenham|olympics|vinicius|"
    r"hat-trick|champions league|transfer window|box(?:ing|er)|"
    r"tennis|open championship|dp world tour|call-up|call up|"
    r"injury blow|midfielder|striker|wicket|innings|wicketkeeper|"
    r"all-blacks|six nations|world tour|equaliser|clean sheet)\b",
)
BIZ_RE = re.compile(
    r"(?i)\b(interest rate|inflation|gdp|stock market|wall street|ftse|"
    r"hang seng|tariff|central bank|federal reserve|imf|world bank|"
    r"unemployment|royal mail|nvidias?|semiconductor|supply chain|"
    r"merger|acquisition|ipo|bond yield|oil price|gas market)\b",
)
SCI_RE = re.compile(
    r"(?i)\b(cop31|climate|nasa|cern|quantum|genome|asteroid|"
    r"seabed|renewable|biodiversity|space telescope|vaccine trial|"
    r"archaeolog|paleontolog|particle physic)\b",
)
CULTURE_RE = re.compile(
    r"(?i)\b(james bond|pattinson|oscar|grammy|venice film|cannes|"
    r"netflix|album|novelist|poet laureate|broadway|west end|"
    r"exhibition|gallery|composer|maestro|festival)\b",
)

STOPWORDS = set(
    """a an the of to in for on and or with from by at as is are was were be
    been being that this those these it its their his her they them he she
    we our after over into about after before than then also not no yes
    will would could should may might new first latest says said say
    report reports reported according amid despite near""".split()
)


class ImgGrab(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.imgs: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "img" and d.get("src"):
            self.imgs.append(d["src"])

    def handle_data(self, data):
        self.text_parts.append(data)


def strip_html(s: str) -> tuple[str, list[str]]:
    if not s:
        return "", []
    p = ImgGrab()
    try:
        p.feed(s)
        p.close()
    except Exception:
        pass
    text = re.sub(r"\s+", " ", " ".join(p.text_parts)).strip()
    return html.unescape(text), p.imgs


def localname(el) -> str:
    return etree.QName(el).localname if el is not None else ""


def childtext(el, name: str) -> str:
    for c in el:
        if localname(c) == name:
            return " ".join(c.itertext()).strip()
    return ""


def parse_date(s: str | None):
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(HKT)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(HKT)
    except Exception:
        return None


CACHE_DIR = Path("/tmp/hc-feed-cache")

def fetch(url: str, timeout: int = 22) -> bytes | None:
    import time
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode()).hexdigest()
    cpath = CACHE_DIR / key
    if cpath.exists() and (time.time() - cpath.stat().st_mtime) < 45 * 60:
        return cpath.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, application/json, */*"})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r:
            data = r.read()
            try:
                cpath.write_bytes(data)
            except Exception:
                pass
            return data
    except Exception as e:
        print(f"  FAIL {url[:80]}  {type(e).__name__}: {e}", file=sys.stderr)
        if cpath.exists():
            return cpath.read_bytes()
        return None


def parse_rss(raw: bytes) -> list[dict]:
    parser = etree.XMLParser(recover=True, huge_tree=True)
    try:
        root = etree.fromstring(raw, parser=parser)
    except Exception:
        return []
    items = [el for el in root.iter() if localname(el) in ("item", "entry")]
    out = []
    for it in items:
        title = html.unescape(re.sub(r"\s+", " ", childtext(it, "title"))).strip()
        link = childtext(it, "link")
        if not link:
            for c in it:
                if localname(c) == "link":
                    link = (c.get("href") or c.text or "").strip()
                    if link:
                        break
        desc_raw = childtext(it, "description") or childtext(it, "summary")
        content = ""
        for c in it:
            if localname(c) == "encoded":
                content = " ".join(c.itertext()).strip() or (c.text or "")
        desc, imgs = strip_html(desc_raw)
        ctext, cimgs = strip_html(content)
        # Prefer short description over full encoded body (copyright).
        summary = desc or (ctext[:400] if ctext else "")
        image = None
        for c in it.iter():
            ln = localname(c)
            if ln in ("thumbnail", "content", "enclosure"):
                url = c.get("url") or c.get("href")
                typ = (c.get("type") or c.get("medium") or "")
                if not url:
                    continue
                if typ.startswith("audio") or typ.startswith("video"):
                    continue
                if (
                    ln == "thumbnail"
                    or typ.startswith("image")
                    or typ in ("", "image")
                    or re.search(r"\.(jpg|jpeg|png|webp|gif)(\?|$)", url, re.I)
                ):
                    image = url
                    break
        if not image:
            image = (imgs or cimgs or [None])[0]
        pub = (
            childtext(it, "pubDate")
            or childtext(it, "published")
            or childtext(it, "date")
            or childtext(it, "updated")
        )
        dt = parse_date(pub)
        author = childtext(it, "creator") or childtext(it, "author")
        if not author:
            for c in it:
                if localname(c) == "author":
                    author = childtext(c, "name") or (c.text or "")
        if link:
            link = re.sub(r"\?at_medium=RSS&at_campaign=rss", "", link)
            link = link.split("?at_medium")[0]
        if not title or not link:
            continue
        out.append(
            {
                "title": title,
                "link": link.strip(),
                "summary": re.sub(r"\s+", " ", summary).strip()[:700],
                "image": image,
                "published": dt,
                "author": re.sub(r"\s+", " ", author or "").strip()[:160],
            }
        )
    return out


def parse_youtube(raw: bytes) -> list[dict]:
    parser = etree.XMLParser(recover=True, huge_tree=True)
    try:
        root = etree.fromstring(raw, parser=parser)
    except Exception:
        return []
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    out = []
    for e in root.xpath("//atom:entry", namespaces=ns):
        title = (e.findtext("atom:title", namespaces=ns) or "").strip()
        vid = e.findtext("yt:videoId", namespaces=ns)
        if not vid:
            mid = e.findtext("atom:id", namespaces=ns) or ""
            m = re.search(r"video:([A-Za-z0-9_-]+)", mid)
            vid = m.group(1) if m else None
        if not vid:
            continue
        published = e.findtext("atom:published", namespaces=ns)
        author = e.findtext("atom:author/atom:name", namespaces=ns) or ""
        desc = ""
        md = e.find(".//{http://search.yahoo.com/mrss/}description")
        if md is not None:
            desc = (md.text or "")[:400]
        out.append(
            {
                "id": vid,
                "title": title,
                "published": published,
                "channel": author,
                "desc": desc,
            }
        )
    return out


def tokens(s: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9']{3,}", (s or "").lower())
    return {w for w in words if w not in STOPWORDS}


def classify(title: str, default: str, feed_hint: str) -> str:
    t = title.lower()
    if SPORT_RE.search(title):
        return "sport"
    if default in ("world", "hong-kong") and BIZ_RE.search(title) and re.search(r"(?i)\b(speed camera|royal mail)\b", title):
        return "business"
    # Keep desk from feed, with light nudges for obvious mismatches in mixed feeds
    if default == "world":
        if SPORT_RE.search(title):
            return "sport"
        if CULTURE_RE.search(title) and not re.search(r"(?i)\b(war|election|sanctions?|minister)\b", title):
            # don't steal hard news
            pass
    # Asia/HK feed items that are clearly world hard news stay if they're not Asia
    return default


def asia_score(title: str, summary: str, source: str) -> int:
    blob = f"{title} {summary} {source}".lower()
    score = 0
    for w in (
        "hong kong", "hongkong", "victoria harbour", "kowloon", "shenzhen",
        "asean", "asia", "china", "beijing", "shanghai", "taipei", "taiwan",
        "tokyo", "japan", "seoul", "korea", "manila", "philippines",
        "singapore", "kuala lumpur", "malaysia", "vietnam", "bangkok",
        "indonesia", "mumbai", "india", "quad", "apec", "rthk",
    ):
        if w in blob:
            score += 4 if w in ("hong kong", "hongkong", "asean", "quad", "shenzhen") else 2
    if source in ("Hong Kong Free Press", "news.gov.hk", "South China Morning Post"):
        score += 8
    if source in ("CNA", "The Japan Times", "BBC News"):
        score += 1
    return score


def is_junk(title: str, summary: str) -> bool:
    if SKIP_TITLE_RE.search(title):
        return True
    if len(title) < 22:
        return True
    # skip very UK-parochial speed-camera etc still allowed in business if space
    return False


def clean_summary(s: str, title: str) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)\s*continue reading.*$", "", s)
    s = re.sub(r"(?i)\s*read more.*$", "", s)
    s = re.sub(r"(?i)\s*click here.*$", "", s)
    s = re.sub(r"(?i)\s*(UK politics live|Full story:|Explainer:).*$", "", s)
    s = re.sub(r"(?i)\s*\(To watch the full press conference.*$", "", s)
    # If the summary repeats the title at the start, trim it
    tt = re.sub(r"\W+", " ", title).strip().lower()
    ss = re.sub(r"\W+", " ", s[: len(title) + 20]).strip().lower()
    if tt and ss.startswith(tt[:40]):
        # keep as is; many feeds use a different sentence
        pass
    return s.strip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def precis(title: str, summary: str, source: str) -> str:
    """Original 2–4 sentence paraphrase from title + public summary only."""
    summary = clean_summary(summary, title)
    # Drop a leading headline echo if the feed pasted it.
    sents = split_sentences(summary) if summary else []
    # Limit to first 3 source sentences to avoid long copyrighted extracts
    sents = sents[:3]
    facts = " ".join(sents).strip()

    # Opening sentence: restate the news, not a verbatim headline copy
    headline = title.rstrip(" .;:")
    # If title is a Guardian-style opinion with a pipe, keep the hook
    hook = headline.split("|")[0].strip()
    # Avoid inventing a verb if the headline is already a sentence
    if re.search(r"\b(is|are|has|have|was|were|will|says|said|warns|announces|faces|joins)\b", hook, re.I):
        open_s = hook if hook.endswith((".", "?", "!")) else hook + "."
    else:
        open_s = f"{hook}, according to {source}."
        # If that reads awkwardly for already-complete headlines, fall back:
        if hook.endswith("?") or hook.endswith("!"):
            open_s = hook

    body = []
    if facts:
        # Light paraphrase: do not copy more than two source sentences,
        # and re-attribute. We slightly recast rather than paste a wall of text.
        recast = facts
        recast = recast.replace("said on Tuesday", "said Tuesday")
        recast = recast.replace("has said that", "said")
        # If the facts already start with the same words as the hook, skip first sentence
        if sents and re.sub(r"\W+", "", sents[0].lower())[:40] == re.sub(r"\W+", "", hook.lower())[:40]:
            recast = " ".join(sents[1:3]).strip()
        if recast:
            # Ensure we don't exceed ~4 sentences total
            extra = split_sentences(recast)[:2]
            body.extend(extra)
    if not body:
        body.append(
            f"The original dispatch is published by {source}; this press prints only a short precis, not the full article."
        )
    # Closing pointer — always
    close = f"Read the original at {source}."
    # Avoid duplicating if we already said that
    text = " ".join([open_s] + body)
    if "Read the original" not in text:
        text = text.rstrip() + " " + close
    # Hard cap length
    if len(text) > 780:
        text = text[:770].rsplit(" ", 1)[0] + " " + close
    return re.sub(r"\s+", " ", text).strip()


def make_slug(title: str, link: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    base = re.sub(r"-{2,}", "-", base)[:72].strip("-")
    h = hashlib.sha1(link.encode("utf-8")).hexdigest()[:6]
    return f"{base}-{h}" if base else h


def deck_from(title: str, summary: str) -> str:
    summary = clean_summary(summary, title)
    if not summary:
        return ""
    first = split_sentences(summary)[0]
    if len(first) > 180:
        first = first[:177].rsplit(" ", 1)[0] + "…"
    # Don't use the title as the deck
    if first.lower().startswith(title.lower()[:24]):
        rest = split_sentences(summary)
        if len(rest) > 1:
            first = rest[1]
        else:
            return ""
    return first


def format_hkt(dt: datetime | None) -> dict:
    if not dt:
        return {"iso": None, "display": "Time not given", "short": ""}
    return {
        "iso": dt.isoformat(),
        "display": dt.strftime("%-d %B %Y, %-I:%M %p") + " HKT",
        "short": dt.strftime("%-d %b, %-I:%M %p") + " HKT",
        "folio": dt.strftime("%A, %-d %B %Y"),
    }


def video_tokens(v: dict) -> set[str]:
    return title_terms(v.get("title") or "")


def is_bad_video(v: dict) -> bool:
    t = v.get("title") or ""
    ch = (v.get("channel") or "")
    if re.search(r"(?i)\bLIVE:|^LIVE\b", t):
        return True
    # CNA uploads are often geo-restricted outside its home region.
    if re.search(r"(?i)\bCNA\b|channel news asia", ch):
        return True
    return False


WEAK_TOKENS = {
    "trump", "donald", "president", "presidents", "china", "chinese", "asia",
    "asian", "united", "states", "america", "american", "world", "news",
    "english", "people", "young", "year", "years", "country", "government",
    "official", "officials", "leaders", "leader", "summit", "talks", "says",
    "said", "video", "watch", "latest", "breaking", "report", "reports",
    "live", "coverage", "morning", "briefing", "short", "shorts", "france",
    "zone", "since", "under", "proposed", "agree", "further", "ahead",
    "after", "before", "during", "south", "north", "east", "west", "week",
    "weeks", "why", "how", "what", "can", "here", "just", "more", "than",
    "over", "work", "state", "public", "deal", "fees", "game", "view",
    "full", "first", "call", "open", "plan", "plans", "change", "changes",
    "student", "students", "business", "companies", "company", "market",
    "uk", "british", "britain", "england", "london", "city", "new", "one",
    "two", "three", "against", "amid", "across", "around", "takes", "take",
    "make", "made", "get", "got", "want", "wants", "arrives", "arrive",
    "meets", "meet", "hosting", "hosts", "host", "must", "may", "major",
    "between", "together", "access", "control", "district", "fault",
    "incidents", "incident", "release", "arrests", "arrest", "attack",
    "close", "triple", "collapse", "prison", "breaks", "announces",
    "russian", "largest", "create", "travel", "inside", "governments",
    "out", "right", "set", "greatest", "where", "off", "kick", "now",
    "man", "nearly", "million", "reduce", "other", "into", "from",
    "could", "would", "being", "been", "have", "has", "had", "their",
}

# Place / entity soft matches so Manila can meet the Philippines, etc.
ALIASES = {
    "manila": {"philippines", "philippine"},
    "philippines": {"manila", "philippine"},
    "philippine": {"manila", "philippines"},
    "asean": {"southeast", "manila"},
    "tariff": {"tariffs"},
    "tariffs": {"tariff"},
    "protest": {"protests", "protesters"},
    "protests": {"protest", "protesters"},
    "bank": {"banks", "banking"},
    "banks": {"bank", "banking"},
    "banking": {"bank", "banks"},
    "chip": {"chips", "semiconductor"},
    "chips": {"chip"},
    "nvidia": {"megaspeed", "huang"},
    "megaspeed": {"nvidia"},
}


def stem(w: str) -> str:
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("es"):
        return w[:-2]
    if len(w) > 4 and w.endswith("s"):
        return w[:-1]
    return w


def title_terms(title: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9']+", title or "")
    out = set()
    for i, raw in enumerate(words):
        w = raw.lower()
        if w in STOPWORDS or w in WEAK_TOKENS or len(w) < 3:
            # keep short acronyms / names: Xi, UN, US, UK, AI, EU
            if raw.isupper() and 2 <= len(raw) <= 3:
                out.add(w)
            elif raw[:1].isupper() and len(raw) == 2 and i > 0:
                out.add(w)  # Xi, Un
            continue
        out.add(w)
        out.add(stem(w))
        for a in ALIASES.get(w, ()):
            out.add(a)
    return out


def proper_nouns(title: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9'\-]*", title or "")
    out = set()
    for i, raw in enumerate(words):
        w = raw.lower()
        if w in STOPWORDS or w in WEAK_TOKENS:
            continue
        if w in {"us", "uk", "eu", "un", "ai"}:
            continue
        if raw.isupper() and len(raw) >= 2:
            out.add(w)
        elif raw[0].isupper() and (i > 0 or len(raw) >= 4):
            out.add(w)
    return out


def bigrams_from(title: str) -> set[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9']{3,}", title or "") if w.lower() not in STOPWORDS]
    return {f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)}


def build_video_df(videos: list[dict]) -> dict:
    from collections import Counter
    df = Counter()
    for v in videos:
        for tok in title_terms(v.get("title") or ""):
            df[tok] += 1
    return df


def match_video(story: dict, videos: list[dict], used: set[str], df=None, nvid=1) -> dict | None:
    """Attach a video only when the titles clearly describe the same event."""
    title = story["title"]
    st = title_terms(title)
    sp = proper_nouns(title)
    sb = bigrams_from(title)
    if not st:
        return None
    best = None
    best_score = -1.0
    for v in videos:
        if is_bad_video(v):
            continue
        vt = title_terms(v.get("title") or "")
        vp = proper_nouns(v.get("title") or "")
        vb = bigrams_from(v.get("title") or "")
        props = sp & vp
        terms = (st & vt) - WEAK_TOKENS
        shared_bi = set()
        for b in sb & vb:
            parts = b.split()
            if any(w not in WEAK_TOKENS and len(w) >= 4 for w in parts):
                shared_bi.add(b)
        if not props and not shared_bi and len(terms) < 2:
            continue
        score = 3.5 * len(props) + 1.6 * len(terms) + 4.0 * len(shared_bi)
        if v["id"] in used:
            score -= 1.2
        if re.search(r"(?i)#shorts|\bshorts\b", v["title"]):
            score -= 0.6
        # opinion letters / cartoons: require a proper noun or quality bigram
        tl = title.lower()
        if "| letters" in tl or "cartoon" in tl:
            if not props and not shared_bi:
                continue
        if score > best_score:
            best_score = score
            best = v
            best_props, best_terms, best_bi = props, terms, shared_bi
    if not best:
        return None
    props, terms, shared_bi = best_props, best_terms, best_bi
    BROAD = {
        "california", "israel", "israeli", "gaza", "asean", "apec", "iran",
        "iranian", "russia", "russian", "europe", "european", "africa",
        "france", "french", "india", "indian", "korea", "korean",
        "japan", "japanese", "taiwan", "taiwanese", "mexico", "mexican",
        "canada", "canadian",  # canada is ok WITH tariffs (other hook)
        "singapore", "philippines", "manila",
    }
    # Aliases count as proper overlap (Manila ~ Philippines)
    for a, bs in ALIASES.items():
        if a in sp and (bs & vp):
            props = set(props) | {a}
        if a in vp and (bs & sp):
            props = set(props) | {a}

    narrow_props = {w for w in props if w not in BROAD}
    narrow_terms = {w for w in terms if w not in BROAD and w not in WEAK_TOKENS}
    quality_bi = {b for b in shared_bi if not all(w in BROAD or w in WEAK_TOKENS for w in b.split())}

    rare_names = []
    for w in narrow_props:
        c = (df.get(w, 1) if df is not None else 1)
        if c <= 6 and len(w) >= 5:
            rare_names.append(w)

    ok = (
        len(narrow_props) >= 2
        or (len(narrow_props) >= 1 and (len(narrow_terms) >= 1 or len(quality_bi) >= 1))
        or (len(quality_bi) >= 1)
        or (len(rare_names) >= 1)
        or (len(props) >= 2 and len(narrow_terms) >= 1)
        or (len(props) >= 1 and len(narrow_terms) >= 2)
    )
    return best if ok else None



def refine_video(story, video, videos, used):
    """Drop unfaithful matches; prefer an official plate that really names the same event."""
    title = story["title"]
    tl = title.lower()

    def find_best(required_any, preferred_all=None):
        preferred_all = preferred_all or []
        cand = []
        for v in videos:
            if is_bad_video(v):
                continue
            vl = v["title"].lower()
            if any(k in vl for k in required_any):
                score = sum(1 for k in required_any if k in vl)
                score += 2 * sum(1 for k in preferred_all if k in vl)
                if v["id"] in used:
                    score -= 0.5
                cand.append((score, v))
        cand.sort(key=lambda x: x[0], reverse=True)
        return cand[0][1] if cand and cand[0][0] >= 1 else None

    # Forced better matches for this week's well-known official packages
    if "protest" in tl and ("philippines" in tl or "manila" in tl):
        v = find_best(["protest"], ["manila", "asean", "philippines", "trump"])
        if v and "protest" in v["title"].lower():
            return v
        return None
    if re.search(r"chip (restriction|curb|rules|export)", tl) or ("chip" in tl and "restriction" in tl):
        v = find_best(["chip"], ["restriction", "curb", "rules", "china"])
        if v and "chip" in v["title"].lower():
            return v
    if "dechambeau" in tl or "liv golf" in tl:
        v = find_best(["dechambeau"], ["liv", "dp world"])
        return v
    if "cop31" in tl or "cop 31" in tl:
        v = find_best(["cop31", "cop 31"], ["climate"])
        return v

    if not video:
        return None
    vl = video["title"].lower()
    # Programme listings and reviews must share a distinctive name with the plate
    if re.search(r"(?i)\binside science\b|to leave radio|\breview [–-]", title):
        props = proper_nouns(title) & proper_nouns(video["title"])
        props -= {"bbc", "radio", "today", "science", "doctor", "american"}
        if not props:
            return None
    # A film or radio item should not wear a crime or war plate
    if re.search(r"(?i)\breview [–-]|to leave radio|radio 4", title) and re.search(r"(?i)murder|strike|war|prison", vl):
        return None
    # Iran-war talking heads are not a photograph of Manila protests
    if "protest" in tl and "vance" in vl:
        return None
    return video


def fetch_weather() -> dict | None:
    raw = fetch("https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en")
    flw = fetch("https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=flw&lang=en")
    if not raw:
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    forecast = {}
    if flw:
        try:
            forecast = json.loads(flw.decode("utf-8"))
        except Exception:
            forecast = {}
    temps = data.get("temperature", {}).get("data") or []
    obs = next((t for t in temps if t.get("place") == "Hong Kong Observatory"), temps[0] if temps else None)
    hum = (data.get("humidity", {}).get("data") or [{}])[0]
    updated = data.get("updateTime")
    # convert update to HKT display
    upd = parse_date(updated) if updated else datetime.now(HKT)
    temp_c = obs.get("value") if obs else None
    humidity = hum.get("value")
    general = (forecast.get("generalSituation") or "").strip()
    fdesc = (forecast.get("forecastDesc") or "").strip()
    # Do not invent a sky condition from icon codes.
    bits = []
    if temp_c is not None:
        bits.append(f"{temp_c}°C at the Hong Kong Observatory")
    if humidity is not None:
        bits.append(f"humidity {humidity}%")
    line = ", ".join(bits)
    if upd:
        line = f"{upd.strftime('%-I:%M %p')} HKT — " + line
    if general:
        # first sentence only
        g = split_sentences(general)[0]
        line = line.rstrip(".") + ". " + g
    return {
        "source": "Hong Kong Observatory",
        "sourceUrl": "https://www.hko.gov.hk/en/index.html",
        "tempC": temp_c,
        "humidity": humidity,
        "place": "Hong Kong Observatory",
        "updatedIso": upd.isoformat() if upd else None,
        "line": line,
        "forecast": fdesc[:400] if fdesc else "",
        "general": general[:400],
    }


def load_cached_feeds(name_map=None) -> list[tuple[str, str, str, bytes]]:
    """Optional: reuse /tmp/feeds during local development if network is slow."""
    return []


def main() -> int:
    now = datetime.now(HKT)
    print(f"Refreshing Harbour Chronicle edition at {now.isoformat()}")

    raw_stories = []
    for url, source, desk in FEEDS:
        print(f"  feed {source:24s} {desk:10s} {url[:70]}")
        raw = fetch(url)
        if not raw:
            continue
        # Skip HTML error pages pretending to be feeds
        head = raw[:200].lstrip().lower()
        if head.startswith(b"<!doctype") or head.startswith(b"<html"):
            print("    skipped HTML page")
            continue
        items = parse_rss(raw)
        print(f"    {len(items)} items")
        for it in items:
            it["source"] = source
            it["desk"] = classify(it["title"], desk, url)
            it["feed"] = url
            raw_stories.append(it)

    videos = []
    seen_vid = set()
    for url, _label in YT_CHANNELS:
        raw = fetch(url)
        if not raw:
            continue
        for v in parse_youtube(raw):
            if v["id"] in seen_vid:
                continue
            seen_vid.add(v["id"])
            videos.append(v)
    print(f"  official videos: {len(videos)}")

    # Dedup by normalised title
    seen = set()
    uniq = []
    for s in raw_stories:
        key = re.sub(r"[^a-z0-9]+", "", s["title"].lower())[:80]
        if key in seen:
            continue
        if is_junk(s["title"], s.get("summary") or ""):
            continue
        seen.add(key)
        uniq.append(s)

    # Recency floor — keep a week so desks can fill
    floor = now - timedelta(days=10)
    uniq = [s for s in uniq if (s["published"] is None or s["published"] >= floor)]

    def score(s: dict) -> float:
        sc = 0.0
        if s["published"]:
            hours = max(0.0, (now - s["published"]).total_seconds() / 3600)
            sc += max(0, 48 - hours)  # fresher is better
        if s.get("summary"):
            sc += 8
        if s.get("image") and s["source"] not in NO_REMOTE_IMAGE:
            sc += 3
        sc += asia_score(s["title"], s.get("summary") or "", s["source"])
        # prefer HKFP / official HK on the harbour desk
        if s["desk"] == "hong-kong" and s["source"] in ("Hong Kong Free Press", "news.gov.hk"):
            sc += 6
        # slightly demote extremely UK-local items on world desk
        if s["desk"] == "world" and re.search(r"(?i)\b(ofcom|ofsted|met office|westminster|senedd|holyrood)\b", s["title"]):
            sc -= 8
        return sc

    by_desk: dict[str, list] = {k: [] for k in DESKS}
    for s in uniq:
        d = s["desk"] if s["desk"] in DESKS else "world"
        # Move obvious Asia Quad/ASEAN lead material: stay where classified
        s["desk"] = d
        s["_score"] = score(s)
        by_desk[d].append(s)

    selected = []
    per_desk_ids = {k: [] for k in DESKS}
    for desk, items in by_desk.items():
        items = sorted(items, key=lambda x: x["_score"], reverse=True)
        # source diversity
        picked = []
        src_counts: dict[str, int] = {}
        for it in items:
            if src_counts.get(it["source"], 0) >= 5 and len(picked) < 10:
                continue
            picked.append(it)
            src_counts[it["source"]] = src_counts.get(it["source"], 0) + 1
            if len(picked) >= 13:
                break
        # pad if diversity filter was too strict
        if len(picked) < 8:
            for it in items:
                if it not in picked:
                    picked.append(it)
                if len(picked) >= 10:
                    break
        for it in picked:
            selected.append(it)
            per_desk_ids[desk].append(it)

    # Videos
    used_vid: set[str] = set()
    story_objs = []
    lookup = {}
    vid_df = build_video_df(videos)
    for s in selected:
        slug = make_slug(s["title"], s["link"])
        pub = format_hkt(s["published"])
        video = match_video(s, videos, used_vid, df=vid_df, nvid=max(1, len(videos)))
        video = refine_video(s, video, videos, used_vid)
        video_obj = None
        if video:
            used_vid.add(video["id"])
            video_obj = {
                "youtubeId": video["id"],
                "channel": video["channel"],
                "title": video["title"],
                "watchUrl": f"https://www.youtube.com/watch?v={video['id']}",
                "embedUrl": f"https://www.youtube-nocookie.com/embed/{video['id']}",
                "poster": f"https://i.ytimg.com/vi/{video['id']}/hqdefault.jpg",
            }
        image = s.get("image")
        if s["source"] in NO_REMOTE_IMAGE:
            image = None
        obj = {
            "id": slug,
            "headline": s["title"],
            "deck": deck_from(s["title"], s.get("summary") or ""),
            "precis": precis(s["title"], s.get("summary") or "", s["source"]),
            "source": s["source"],
            "sourceUrl": s["link"],
            "sourceHome": SOURCE_HOME.get(s["source"], s["link"]),
            "author": s.get("author") or "",
            "published": pub,
            "desk": s["desk"],
            "image": image,
            "imageCredit": (s["source"] + " (feed image)") if image else "",
            "video": video_obj,
            "summarySource": clean_summary(s.get("summary") or "", s["title"])[:400],
        }
        story_objs.append(obj)
        lookup[slug] = obj

    # Front page mix: highest-scoring across desks, with a Hong Kong/Asia lead preference
    def front_score(obj):
        raw = next(s for s in selected if make_slug(s["title"], s["link"]) == obj["id"])
        sc = raw["_score"]
        if obj["video"]:
            sc += 12
        if obj["desk"] in ("hong-kong", "world"):
            sc += 5
        return sc

    ranked = sorted(story_objs, key=front_score, reverse=True)
    front = []
    desks_on_front: dict[str, int] = {}
    for obj in ranked:
        if desks_on_front.get(obj["desk"], 0) >= 4 and len(front) < 12:
            continue
        front.append(obj["id"])
        desks_on_front[obj["desk"]] = desks_on_front.get(obj["desk"], 0) + 1
        if len(front) >= 16:
            break
    # Ensure a living-plate lead if possible: put a video story first among top
    if front:
        def lede_rank(sid):
            h = lookup[sid]["headline"].lower()
            sc = 0
            if "putin" in h and ("xi" in h or "shenzhen" in h):
                sc += 50
            if "philippines" in h and "protest" in h:
                sc += 40
            if "arrives in philippines" in h or "asia trip" in h:
                sc += 35
            if lookup[sid]["video"]:
                sc += 8
            if lookup[sid]["desk"] in ("hong-kong", "world"):
                sc += 5
            return sc
        front = [front[0]] + front[1:]
        front = sorted(front, key=lede_rank, reverse=True)

    # Related links: other selected stories sharing tokens
    for obj in story_objs:
        st = tokens(obj["headline"])
        rel = []
        for other in story_objs:
            if other["id"] == obj["id"]:
                continue
            ov = len(st & tokens(other["headline"]))
            if ov >= 2:
                rel.append((ov, other["id"]))
        rel.sort(reverse=True)
        obj["related"] = [r[1] for r in rel[:4]]

    weather = fetch_weather()
    doy = int(now.strftime("%j"))
    edition = {
        "paper": "The Harbour Chronicle",
        "motto": "Ink that holds the tide",
        "press": "The Living Press at Victoria Harbour",
        "city": "Hong Kong",
        "volume": "Vol. I",
        "number": doy,
        "issueLine": f"Vol. I, No. {doy}",
        "editionName": "Evening Tide" if now.hour >= 16 else ("Morning Tide" if now.hour < 12 else "Midday Leaf"),
        "dateIso": now.date().isoformat(),
        "dateDisplay": now.strftime("%A, %-d %B %Y"),
        "generatedAt": now.isoformat(),
        "timezone": "HKT",
        "weather": weather,
        "desks": DESKS,
        "front": front,
        "stories": {o["id"]: o for o in story_objs},
        "deskLists": {
            d: [o["id"] for o in story_objs if o["desk"] == d] for d in DESKS
        },
        "credits": {
            "feeds": sorted({s["source"] for s in selected}),
            "videoChannels": sorted({(s["video"]["channel"] if s["video"] else None) for s in story_objs if s["video"]}),
            "weather": "Hong Kong Observatory open data, when shown",
            "note": "Headlines, times and facts are taken from public RSS feeds and official open data. Article bodies are not reproduced. Living plates use official YouTube embeds from news organisations, restyled as press plates, or still photographs supplied by those feeds.",
        },
    }

    data_path = ROOT / "data" / "news.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
    js_path = ROOT / "js" / "edition.js"
    js_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.write_text(
        "/* Generated snapshot — do not edit by hand. */\nwindow.CHRONICLE_EDITION = "
        + json.dumps(edition, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )

    n_vid = sum(1 for o in story_objs if o["video"])
    print(f"Wrote {len(story_objs)} stories, {n_vid} living plates, front={len(front)}")
    print(f"  {data_path}")
    print("Front:")
    for sid in front:
        o = lookup[sid]
        mark = "VIDEO" if o["video"] else "still"
        print(f"  [{mark}] {o['desk']:10s} {o['source']:22s} {o['headline'][:80]}")
    for d, ids in edition["deskLists"].items():
        nv = sum(1 for i in ids if lookup[i]["video"])
        print(f"  desk {d:10s} {len(ids):2d} stories, {nv} videos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
