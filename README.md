# The Harbour Chronicle

An independent digital broadsheet, set at the Living Press at Victoria Harbour. It is a made object: cream rag paper, letterpress typography, and *living plates* — official news pictures restyled as muted, looping impressions in typographic frames.

It is not affiliated with any other newspaper, studio, or government.

## What is real, and what is framing

Headlines, times, and facts come from public RSS feeds and official open data. Each story carries a short original precis and a link to the originating publisher. Article bodies are not reproduced. Times are shown in Hong Kong Time (HKT). The harbour glass, when present, is taken from the Hong Kong Observatory.

The magic lives in the object: the press-mark (a harbour egret among typographic tide rings), the mottos, the desk ornaments, and the moving plates. No news, quotation, score, or dateline is invented.

## Local preview

```bash
python3 -m http.server 8765
# open http://127.0.0.1:8765/
```

## Refreshing the edition

```bash
pip install lxml
python3 scripts/refresh_news.py
```

A GitHub Action runs the same script on a schedule and commits a fresh `data/news.json` and `js/edition.js`.

## Licence of this site

The typography, press-mark, rag textures, and original code in this repository are offered for this edition. Third-party news text, photographs, and videos remain the property of their publishers and are used here only as short attributed precis, feed images, or official embeds, with links back to the source.


## Install as an app

This edition is a Progressive Web App. After opening the live leaf, you can keep it on your Home Screen and reopen it full-screen, like a paper in the hand (no browser address bar). Once it has been opened online, the shell and the latest snapshot can also be read again without a wire.

- **iPhone / iPad (Safari):** open the site, tap the Share button, then **Add to Home Screen**. Open *Chronicle* from the Home Screen to read it in standalone mode.
- **Android (Chrome):** open the site, then use the browser menu **Install app**, or the typographic **Install this edition** control in the colophon when it appears.
- **Desktop (Chrome / Edge):** use **Install this edition** in the footer when the browser offers it, or the install icon in the address bar.

An Android APK is not bundled with this repository (no Android SDK was available on the press). The PWA is the supported path for phones, including iPhone.
