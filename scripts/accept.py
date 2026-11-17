#!/usr/bin/env python3
"""Visual and click-through acceptance for The Harbour Chronicle."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "shots"
SHOTS.mkdir(exist_ok=True)
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8877"
ED = json.loads((ROOT / "data" / "news.json").read_text())

ISSUES = []

def issue(msg):
    ISSUES.append(msg)
    print("ISSUE:", msg)

def ok(msg):
    print("OK:", msg)

def main():
    chrome = "/usr/bin/google-chrome"
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=chrome,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        # Desktop front
        page = browser.new_page(viewport={"width": 1280, "height": 1600}, device_scale_factor=1)
        page.goto(BASE + "/index.html", wait_until="load", timeout=60000)
        page.wait_for_selector(".lede .headline", timeout=20000)
        # fonts/images settle
        page.wait_for_timeout(1800)
        title = page.title()
        if "Harbour Chronicle" not in title:
            issue(f"Front title unexpected: {title}")
        else:
            ok(f"Front title: {title}")
        body = page.inner_text("body")
        forbidden = ["Daily Prophet", "Harry Potter", "Hogwarts", "Warner Bros", "Hedwig"]
        for w in forbidden:
            if w.lower() in body.lower():
                issue(f"Forbidden IP term on front: {w}")
        if "Ink that holds the tide" not in body:
            issue("Motto missing on front")
        if "HKT" not in body:
            issue("HKT not visible on front")
        else:
            ok("HKT visible")
        lede = page.locator(".lede .headline").inner_text()
        print("LEDE:", lede)
        if not page.locator(".living-plate, .still-plate").count():
            issue("No plates on the front leaf")
        else:
            ok(f"Plates on front: {page.locator('.living-plate').count()} living, {page.locator('.still-plate').count()} still")
        # overflow check: any element wider than sheet?
        overflow = page.evaluate("""() => {
          const sheet = document.querySelector('.sheet');
          if (!sheet) return ['no sheet'];
          const sw = sheet.getBoundingClientRect().width;
          const bad = [];
          for (const el of sheet.querySelectorAll('h1,h2,h3,p,a,figcaption,article')) {
            const r = el.getBoundingClientRect();
            if (r.width > sw + 8) bad.push(el.tagName + ' ' + (el.innerText||'').slice(0,40));
          }
          return bad.slice(0, 8);
        }""")
        if overflow:
            issue("Overflow on desktop front: " + "; ".join(overflow))
        else:
            ok("No obvious overflow on desktop front")
        page.screenshot(path=str(SHOTS / "front-desktop.png"), full_page=True)
        ok("Wrote front-desktop.png")

        # Nav links
        hrefs = page.eval_on_selector_all(".slug-nav a", "els => els.map(a => ({href:a.getAttribute('href'), text:a.innerText}))")
        print("NAV", hrefs)
        expected = ["index.html","world.html","hong-kong.html","business.html","sport.html","culture.html","science.html","opinion.html"]
        got = [h["href"] for h in hrefs]
        for e in expected:
            if e not in got:
                issue(f"Missing nav link {e}")
        for h in hrefs:
            resp = page.goto(BASE + "/" + h["href"], wait_until="domcontentloaded", timeout=30000)
            if not resp or resp.status >= 400:
                issue(f"Nav {h['href']} status {resp.status if resp else None}")
            else:
                page.wait_for_selector("#folio-body .headline, #folio-body .desk-intro, #folio-body .lede", timeout=15000)
                ok(f"Nav {h['href']} -> {resp.status} title={page.title()[:60]}")
        # Distinct section style: Hong Kong
        page.goto(BASE + "/hong-kong.html", wait_until="load", timeout=60000)
        page.wait_for_selector(".folio-section .headline, .lead-slot .headline", timeout=20000)
        page.wait_for_timeout(1200)
        has_seal = page.locator(".seal-mark").count() > 0
        if not has_seal:
            issue("Hong Kong desk missing vermillion seal")
        else:
            ok("Hong Kong vermillion seal present")
        page.screenshot(path=str(SHOTS / "section-hong-kong-desktop.png"), full_page=True)
        ok("Wrote section-hong-kong-desktop.png")

        # Sport — different typographic personality
        page.goto(BASE + "/sport.html", wait_until="load", timeout=60000)
        page.wait_for_selector(".headline", timeout=20000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(SHOTS / "section-sport-desktop.png"), full_page=False)
        ok("Wrote section-sport-desktop.png")

        # Open at least 8 articles, prefer ones with video
        stories = list(ED["stories"].values())
        with_video = [s for s in stories if s.get("video")]
        without = [s for s in stories if not s.get("video")]
        sample = (with_video[:6] + without[:4])[:10]
        checked = 0
        article_shot = False
        for s in sample:
            url = BASE + "/article.html?id=" + s["id"]
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if not resp or resp.status >= 400:
                issue(f"Article {s['id']} status {resp and resp.status}")
                continue
            page.wait_for_selector("h1.headline", timeout=15000)
            h = page.locator("h1.headline").inner_text().strip()
            if h != s["headline"]:
                issue(f"Article headline mismatch: {h!r} vs {s['headline']!r}")
            if "HKT" not in page.inner_text("body"):
                issue(f"No HKT on article {s['id']}")
            src = page.locator(".source-link a")
            if src.count() < 1:
                issue(f"No source link on {s['id']}")
            else:
                href = src.first.get_attribute("href") or ""
                if not href.startswith("http"):
                    issue(f"Bad source href {href}")
                elif href != s["sourceUrl"]:
                    issue(f"Source href mismatch {href}")
            if s.get("video"):
                # either iframe (after YT API) or a host waiting, plus a watch link
                page.wait_for_timeout(1500)
                watch = page.locator(f'a[href*="{s["video"]["youtubeId"]}"]')
                if watch.count() < 1:
                    issue(f"Missing official watch link for {s['id']}")
                # confirm watch page exists (HEAD)
            # image error?
            broken = page.evaluate("""() => [...document.images].filter(i => i.naturalWidth===0 && i.complete).map(i => i.src)""")
            # living plate iframes may not count as images
            if broken:
                issue(f"Broken images on {s['id']}: {broken[:3]}")
            overflow = page.evaluate("""() => {
              const sheet = document.querySelector('.sheet');
              const sw = sheet.getBoundingClientRect().width;
              return [...sheet.querySelectorAll('h1,p')].some(el => el.getBoundingClientRect().width > sw + 12);
            }""")
            if overflow:
                issue(f"Overflow on article {s['id']}")
            if s.get("video") and not article_shot:
                page.wait_for_timeout(2500)  # let plate attempt to load
                page.screenshot(path=str(SHOTS / "article-video-desktop.png"), full_page=True)
                article_shot = True
                ok("Wrote article-video-desktop.png for " + s["headline"][:60])
            checked += 1
        ok(f"Opened {checked} articles")

        # Mobile front
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        mobile.goto(BASE + "/index.html", wait_until="load", timeout=60000)
        mobile.wait_for_selector(".lede .headline", timeout=20000)
        mobile.wait_for_timeout(1500)
        # squeezed desktop? check if slug-nav overflows in a horizontal scroll way is OK;
        # sheet should be nearly viewport width
        geom = mobile.evaluate("""() => {
          const sheet = document.querySelector('.sheet').getBoundingClientRect();
          const lede = document.querySelector('.lede').getBoundingClientRect();
          return {vw: innerWidth, sheetW: sheet.width, ledeW: lede.width, bodyOverflow: document.body.scrollWidth};
        }""")
        print("MOBILE GEOM", geom)
        if geom["bodyOverflow"] > geom["vw"] + 20:
            issue(f"Mobile horizontal overflow: body {geom['bodyOverflow']} vw {geom['vw']}")
        else:
            ok("Mobile front does not squeeze a desktop layout")
        mobile.screenshot(path=str(SHOTS / "front-mobile.png"), full_page=True)
        ok("Wrote front-mobile.png")

        # 404 and about
        r = mobile.goto(BASE + "/about.html", wait_until="domcontentloaded")
        if r and r.status == 200 and "Colophon" in mobile.inner_text("body"):
            ok("About/colophon loads")
        else:
            issue("About page failed")
        r = mobile.goto(BASE + "/404.html", wait_until="domcontentloaded")
        if r and "never set" in mobile.inner_text("body").lower():
            ok("404 leaf loads")
        else:
            issue("404 page failed")

        browser.close()

    # Verify outgoing source links (sample) and YouTube watch pages
    def head(url):
        req = Request(url, method="HEAD", headers={"User-Agent": "HarbourChronicle/1.0 acceptance"})
        try:
            with urlopen(req, timeout=15) as r:
                return r.status
        except Exception as e:
            # some papers reject HEAD
            try:
                req2 = Request(url, headers={"User-Agent": "HarbourChronicle/1.0 acceptance"})
                with urlopen(req2, timeout=15) as r:
                    return r.status
            except Exception as e2:
                return f"ERR {e2}"

    spot = [ED["stories"][i] for i in ED["front"][:6]]
    for s in spot:
        st = head(s["sourceUrl"])
        print(f"SOURCE {st} {s['source']}: {s['headline'][:70]}")
        if isinstance(st, int) and st >= 400:
            issue(f"Source URL {st} for {s['sourceUrl']}")
        if s.get("video"):
            yt = head(s["video"]["watchUrl"])
            print(f"  YT {yt} {s['video']['watchUrl']}")
            if isinstance(yt, int) and yt >= 400:
                issue(f"YouTube watch {yt} {s['video']['watchUrl']}")

    # Times in HKT in snapshot
    bad_times = [s["id"] for s in ED["stories"].values() if s.get("published") and s["published"].get("display") and "HKT" not in s["published"]["display"]]
    if bad_times:
        issue(f"Stories missing HKT label: {len(bad_times)}")
    else:
        ok("All dated stories are labeled HKT in the snapshot")

    print("\n==== ACCEPTANCE SUMMARY ====")
    print("issues:", len(ISSUES))
    for i in ISSUES:
        print(" -", i)
    return 1 if ISSUES else 0

if __name__ == "__main__":
    sys.exit(main())
