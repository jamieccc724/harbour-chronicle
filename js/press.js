/* The Harbour Chronicle — Living Press compositor. */
(function () {
  "use strict";

  const DESK_ORDER = ["world", "hong-kong", "business", "sport", "culture", "science", "opinion"];
  const DESK_HREF = {
    world: "world.html",
    "hong-kong": "hong-kong.html",
    business: "business.html",
    sport: "sport.html",
    culture: "culture.html",
    science: "science.html",
    opinion: "opinion.html",
  };

  const ytPlayers = {};
  let ytReady = false;
  const ytQueue = [];

  window.onYouTubeIframeAPIReady = function () {
    ytReady = true;
    ytQueue.forEach(fn => fn());
  };

  function edition() {
    return window.CHRONICLE_EDITION || null;
  }

  function story(id) {
    const ed = edition();
    return ed && ed.stories ? ed.stories[id] : null;
  }

  function pageKind() {
    return document.body.getAttribute("data-leaf") || "front";
  }

  function pageDesk() {
    return document.body.getAttribute("data-desk") || "world";
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function firstLetter(text) {
    const m = String(text || "").trim().match(/[\p{L}\p{N}]/u);
    return m ? m[0] : "";
  }

  function tidyPrecis(s, text) {
    let t = String(text || "");
    const h = String((s && s.headline) || "").replace(/[\s.]+$/, "").trim();
    if (h && t.toLowerCase().indexOf(h.toLowerCase()) === 0) {
      t = t.slice(h.length).replace(/^,\s*according to [^.]+\.\s*/i, "").replace(/^\.\s*/, "").trim();
    }
    return t;
  }

  function precisHtml(text, drop, storyObj) {
    const t = tidyPrecis(storyObj, text);
    if (!drop) return escapeHtml(t);
    const ch = firstLetter(t);
    if (!ch) return escapeHtml(t);
    const i = t.indexOf(ch);
    const before = t.slice(0, i);
    const after = t.slice(i + ch.length);
    return escapeHtml(before) + '<span class="drop">' + escapeHtml(ch) + "</span>" + escapeHtml(after);
  }

  function plateCaption(s, index) {
    const n = String(index).padStart(2, "0");
    const kind = s.video ? "Living plate" : "Still plate";
    const from = s.video ? s.video.channel : (s.imageCredit || s.source);
    const t = s.published && s.published.short ? s.published.short : "";
    return kind + " " + n + " — after " + from + (t ? ", " + t : "") + ".";
  }

  function plateHtml(s, index, opts) {
    opts = opts || {};
    const cap = escapeHtml(plateCaption(s, index));
    if (s.video && s.video.youtubeId) {
      const id = s.video.youtubeId;
      const poster = s.video.poster || ("https://i.ytimg.com/vi/" + id + "/hqdefault.jpg");
      const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const start = reduced ? "paused" : "live";
      return (
        '<figure class="living-plate" data-yt="' + escapeHtml(id) + '" data-watch="' + escapeHtml(s.video.watchUrl) + '" data-motion="' + start + '">' +
          '<div class="plate-well">' +
            '<div class="plate-skel" aria-hidden="true"></div>' +
            '<div class="plate-crop">' +
              '<img class="plate-poster" src="' + escapeHtml(poster) + '" alt="" onerror="this.onerror=null;this.src=\'assets/images/plate-fallback.jpg\';">' +
              (reduced ? "" : '<div data-yt-host="1"></div>') +
            '</div>' +
            '<div class="plate-grain" aria-hidden="true"></div>' +
            '<div class="plate-vignette" aria-hidden="true"></div>' +
            '<button type="button" class="plate-sound" aria-pressed="false" aria-label="Sound for this plate">Sound off</button>' +
          '</div>' +
          '<figcaption class="plate-cap">' + cap +
            ' <a class="source-link" href="' + escapeHtml(s.video.watchUrl) + '" rel="noopener noreferrer">Watch at ' + escapeHtml(s.video.channel) + '</a>' +
          '</figcaption>' +
        '</figure>'
      );
    }
    const img = s.image || "assets/images/plate-fallback.jpg";
    const alt = s.headline ? ("Illustration for: " + s.headline) : "A still press plate";
    return (
      '<figure class="still-plate">' +
        '<div class="plate-well">' +
          '<div class="plate-crop"><img src="' + escapeHtml(img) + '" alt="' + escapeHtml(alt) + '" loading="lazy" onerror="this.onerror=null;this.src=\'assets/images/plate-fallback.jpg\';"></div>' +
          '<div class="plate-grain" aria-hidden="true"></div>' +
          '<div class="plate-vignette" aria-hidden="true"></div>' +
        '</div>' +
        '<figcaption class="plate-cap">' + cap + '</figcaption>' +
      '</figure>'
    );
  }

  function storyUrl(id) {
    return "article.html?id=" + encodeURIComponent(id);
  }

  function metaLine(s) {
    const bits = [];
    if (s.source) bits.push(escapeHtml(s.source));
    if (s.author) bits.push(escapeHtml(s.author));
    if (s.published && s.published.display) bits.push(escapeHtml(s.published.display));
    return bits.join(" · ");
  }

  function storyBlock(s, opts) {
    opts = opts || {};
    const level = opts.level || "h3";
    const drop = !!opts.drop;
    const plate = opts.plate ? plateHtml(s, opts.plateIndex || 1, opts) : "";
    const deck = s.deck && !opts.tight ? '<p class="deck">' + escapeHtml(s.deck) + "</p>" : "";
    const precis = opts.noPrecis ? "" : '<p class="precis">' + precisHtml(s.precis, drop, s) + "</p>";
    const klass = "story-block" + (opts.tight ? " tight" : "") + (opts.rule ? " rule-heavy" : "");
    return (
      '<article class="' + klass + '" data-id="' + escapeHtml(s.id) + '">' +
        (opts.kicker ? '<p class="kicker">' + escapeHtml(opts.kicker) + "</p>" : "") +
        (opts.plateFirst ? plate : "") +
        "<" + level + ' class="headline"><a href="' + storyUrl(s.id) + '">' + escapeHtml(s.headline) + "</a></" + level + ">" +
        deck +
        '<p class="dateline">' + metaLine(s) + "</p>" +
        (opts.plateFirst ? "" : plate) +
        precis +
        '<p class="source-link"><a href="' + escapeHtml(s.sourceUrl) + '" rel="noopener noreferrer">Read the original at ' + escapeHtml(s.source) + "</a></p>" +
      "</article>"
    );
  }

  function fillChrome(ed) {
    const dateEl = document.querySelector("[data-bind=date]");
    if (dateEl) dateEl.textContent = ed.dateDisplay + " · " + (ed.editionName || "") + " · " + ed.city;
    const volEl = document.querySelector("[data-bind=volume]");
    if (volEl) volEl.textContent = ed.issueLine;
    const wEl = document.querySelector("[data-bind=weather]");
    if (wEl) {
      if (ed.weather && ed.weather.line) {
        const href = ed.weather.sourceUrl || "https://www.hko.gov.hk/en/index.html";
        wEl.innerHTML = 'Harbour glass — <a href="' + escapeHtml(href) + '" rel="noopener noreferrer">' + escapeHtml(ed.weather.line) + "</a>";
      } else {
        wEl.textContent = "";
      }
    }
    const titleBits = ["The Harbour Chronicle"];
    if (pageKind() === "section") {
      const d = ed.desks[pageDesk()];
      if (d) titleBits.push(d.name);
    }
    if (pageKind() === "article") {
      const params = new URLSearchParams(location.search);
      const s = story(params.get("id") || "");
      if (s) titleBits.unshift(s.headline);
    }
    if (pageKind() === "about") titleBits.push("Colophon");
    if (pageKind() === "lost") titleBits.push("This leaf was never set");
    titleBits.push(ed.dateDisplay);
    document.title = titleBits.join(" — ");

    document.querySelectorAll(".slug-nav a[data-desk]").forEach(a => {
      const on = (pageKind() === "front" && a.getAttribute("data-desk") === "world" && location.pathname.endsWith("index.html") || /\/$|index\.html$/.test(location.pathname)) 
        ? a.getAttribute("data-desk") === "world" && pageKind() === "front"
        : a.getAttribute("data-desk") === pageDesk() && pageKind() !== "about" && pageKind() !== "lost" && (pageKind() === "section" || (pageKind() === "article" && (story(new URLSearchParams(location.search).get("id")||"")||{}).desk === a.getAttribute("data-desk")));
      if (pageKind() === "front" && a.getAttribute("data-desk") === "world" && (location.pathname.endsWith("/") || location.pathname.endsWith("index.html") || location.pathname.endsWith("harbour-chronicle"))) {
        /* Front is the world/front leaf; World slug still points to world.html for the full desk. */
        a.removeAttribute("aria-current");
      }
      if (pageKind() === "section" && a.getAttribute("data-desk") === pageDesk()) {
        a.setAttribute("aria-current", "page");
      }
    });
  }

  function renderFront(ed) {
    const root = document.getElementById("folio-body");
    if (!root) return;
    const ids = (ed.front || []).map(id => story(id)).filter(Boolean);
    if (!ids.length) {
      root.innerHTML = "<p>The press is waiting on this morning’s dispatches.</p>";
      return;
    }
    const lede = ids[0];
    const rest = ids.slice(1);
    const colA = rest.slice(0, 5);
    const colB = rest.slice(5, 10);
    const colC = rest.slice(10, 16);
    let plateN = 1;
    let html = '<div class="folio-front">';
    html += '<section class="lede">';
    html += "<div>";
    html += '<p class="kicker">' + escapeHtml((ed.desks[lede.desk] || {}).flag || "") + " · " + escapeHtml(ed.city) + "</p>";
    html += '<h2 class="headline"><a href="' + storyUrl(lede.id) + '">' + escapeHtml(lede.headline) + "</a></h2>";
    if (lede.deck) html += '<p class="deck">' + escapeHtml(lede.deck) + "</p>";
    html += '<p class="dateline">' + metaLine(lede) + "</p>";
    html += '<p class="precis">' + precisHtml(lede.precis, true, lede) + "</p>";
    html += '<p class="source-link"><a href="' + escapeHtml(lede.sourceUrl) + '" rel="noopener noreferrer">Read the original at ' + escapeHtml(lede.source) + "</a></p>";
    html += "</div><div>";
    html += plateHtml(lede, plateN++, { hero: true });
    html += "</div></section>";

    function col(items, firstPlates) {
      let h = "<div>";
      items.forEach((s, i) => {
        const showPlate = !!(s.video || s.image) && (i < firstPlates);
        h += storyBlock(s, {
          tight: i > 0,
          plate: showPlate,
          plateIndex: showPlate ? plateN++ : 0,
          plateFirst: true,
          noPrecis: i > 0,
        });
      });
      return h + "</div>";
    }
    html += col(colA, 1);
    html += col(colB, 1);
    html += "<div>";
    html += '<p class="kicker">Also on this leaf</p>';
    colC.forEach((s, i) => {
      html += storyBlock(s, { tight: true, plate: i === 0 && !!(s.video || s.image), plateIndex: plateN++, plateFirst: true, noPrecis: true, kicker: (ed.desks[s.desk] || {}).flag });
    });
    html += "</div></div>";
    root.innerHTML = html;
  }

  function renderSection(ed) {
    const root = document.getElementById("folio-body");
    const desk = pageDesk();
    const meta = ed.desks[desk] || {};
    const ids = (ed.deskLists && ed.deskLists[desk]) || [];
    const items = ids.map(story).filter(Boolean);
    const flagExtra = desk === "hong-kong" ? ' <span class="seal-mark" title="Harbour desk seal">港聞</span>' : "";
    let plateN = 1;
    let html = "";
    html += '<header class="desk-head">';
    html += '<p class="section-flag">' + escapeHtml(meta.flag || desk) + '<span class="zh">' + escapeHtml(meta.zh || "") + "</span></p>";
    html += '<p class="desk-kicker">' + escapeHtml(meta.kicker || "") + flagExtra + "</p>";
    html += '<p class="desk-intro">' + escapeHtml(meta.intro || "") + "</p>";
    html += "</header>";
    if (!items.length) {
      html += "<p>No dispatches are on this stone today.</p>";
      root.innerHTML = html;
      return;
    }
    const lead = items[0];
    const rest = items.slice(1);
    html += '<div class="folio-section">';
    html += '<section class="lead-slot">';
    html += "<div>";
    html += '<h2 class="headline"><a href="' + storyUrl(lead.id) + '">' + escapeHtml(lead.headline) + "</a></h2>";
    if (lead.deck) html += '<p class="deck">' + escapeHtml(lead.deck) + "</p>";
    html += '<p class="dateline">' + metaLine(lead) + "</p>";
    html += '<p class="precis">' + precisHtml(lead.precis, true, lead) + "</p>";
    html += '<p class="source-link"><a href="' + escapeHtml(lead.sourceUrl) + '" rel="noopener noreferrer">Read the original at ' + escapeHtml(lead.source) + "</a></p>";
    html += "</div><div>" + plateHtml(lead, plateN++) + "</div></section>";
    rest.forEach((s, i) => {
      html += storyBlock(s, {
        tight: desk !== "culture" && desk !== "opinion" && i > 2,
        plate: !!(s.video || (s.image && i < 6)),
        plateIndex: plateN++,
        plateFirst: desk === "culture" || !!(s.video && i < 4),
        drop: desk === "opinion",
        noPrecis: desk !== "opinion" && desk !== "culture" && i > 7,
      });
    });
    html += "</div>";
    root.innerHTML = html;
  }

  function renderArticle(ed) {
    const root = document.getElementById("folio-body");
    const id = new URLSearchParams(location.search).get("id") || "";
    const s = story(id);
    if (!s) {
      root.innerHTML = '<div class="lost-leaf"><h2 class="headline">This dispatch is not on the stone.</h2><p><a href="index.html">Return to the front leaf</a>.</p></div>';
      return;
    }
    document.body.setAttribute("data-desk", s.desk);
    document.body.classList.remove.apply(document.body.classList, DESK_ORDER.map(d => "desk-" + d));
    document.body.classList.add("desk-" + s.desk);
    const meta = ed.desks[s.desk] || {};
    const related = (s.related || []).map(story).filter(Boolean);
    let html = '<article class="article-leaf">';
    html += "<div>";
    html += '<p class="kicker"><a href="' + (DESK_HREF[s.desk] || "index.html") + '">' + escapeHtml(meta.flag || s.desk) + "</a></p>";
    html += '<h1 class="headline">' + escapeHtml(s.headline) + "</h1>";
    if (s.deck) html += '<p class="deck">' + escapeHtml(s.deck) + "</p>";
    html += '<p class="dateline">' + metaLine(s) + "</p>";
    html += plateHtml(s, 1);
    html += '<p class="precis">' + precisHtml(s.precis, true, s) + "</p>";
    html += '<p class="source-link"><a href="' + escapeHtml(s.sourceUrl) + '" rel="noopener noreferrer">Read the original at ' + escapeHtml(s.source) + "</a></p>";
    html += "</div><aside class=\"related\">";
    html += "<h2>Also set from this week’s stone</h2>";
    if (related.length) {
      html += "<ul>";
      related.forEach(r => {
        html += "<li><a href=\"" + storyUrl(r.id) + "\">" + escapeHtml(r.headline) + "</a> <span class=\"src\">" + escapeHtml(r.source) + "</span></li>";
      });
      html += "</ul>";
    } else {
      html += "<p>No companion leaves are marked for this dispatch.</p>";
    }
    html += "<p class=\"desk-intro\" style=\"margin-top:1.2rem\">" + escapeHtml(meta.intro || "") + "</p>";
    html += "</aside></article>";
    root.innerHTML = html;
    document.querySelectorAll(".slug-nav a[data-desk]").forEach(a => {
      if (a.getAttribute("data-desk") === s.desk) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
  }

  function settlePlate(fig, reason) {
    const well = fig.querySelector(".plate-well");
    const crop = fig.querySelector(".plate-crop");
    const skel = fig.querySelector(".plate-skel");
    const host = fig.querySelector("[data-yt-host]");
    if (well) well.classList.add("is-failed");
    if (crop) crop.classList.remove("is-live");
    if (skel) skel.classList.add("is-done");
    if (host) host.remove();
    fig.setAttribute("data-motion", "still");
  }

  function mountPlates() {
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelectorAll(".living-plate[data-yt]").forEach((fig, i) => {
      const id = fig.getAttribute("data-yt");
      const watch = fig.getAttribute("data-watch") || ("https://www.youtube.com/watch?v=" + id);
      const host = fig.querySelector("[data-yt-host]");
      const btn = fig.querySelector(".plate-sound");
      const skel = fig.querySelector(".plate-skel");
      const poster = fig.querySelector(".plate-poster");
      if (poster) {
        if (poster.complete) { if (skel) skel.classList.add("is-done"); }
        else poster.addEventListener("load", function () { if (skel) skel.classList.add("is-done"); });
        poster.addEventListener("error", function () { if (skel) skel.classList.add("is-done"); });
      } else if (skel) {
        skel.classList.add("is-done");
      }

      const openWatch = function () {
        window.open(watch, "_blank", "noopener");
      };

      if (!host || reduced) {
        if (btn) {
          btn.textContent = "Watch";
          btn.setAttribute("aria-label", "Open the official moving picture");
          btn.addEventListener("click", openWatch);
        }
        return;
      }

      const uid = "plate_" + id.replace(/[^A-Za-z0-9_-]/g, "") + "_" + i;
      const mount = document.createElement("div");
      mount.id = uid;
      host.appendChild(mount);
      let started = false;
      let watchdog;

      const fail = function () {
        if (fig.getAttribute("data-motion") === "still") return;
        try {
          const p = ytPlayers[uid];
          if (p && p.destroy) p.destroy();
        } catch (err) {}
        delete ytPlayers[uid];
        settlePlate(fig);
        if (btn) {
          btn.textContent = "Watch";
          btn.setAttribute("aria-pressed", "false");
          btn.setAttribute("aria-label", "Open the official moving picture");
        }
      };

      const boot = function () {
        if (!window.YT || !window.YT.Player) {
          ytQueue.push(boot);
          return;
        }
        let player;
        try {
          player = new YT.Player(uid, {
            videoId: id,
            host: "https://www.youtube-nocookie.com",
            playerVars: {
              autoplay: 1,
              mute: 1,
              controls: 0,
              modestbranding: 1,
              rel: 0,
              playsinline: 1,
              fs: 0,
              iv_load_policy: 3,
              disablekb: 1,
              cc_load_policy: 0,
              loop: 1,
              playlist: id,
              origin: location.origin,
              enablejsapi: 1,
            },
            events: {
              onReady: function (e) {
                try { e.target.mute(); e.target.playVideo(); } catch (err) {}
                if (skel) skel.classList.add("is-done");
              },
              onError: function () { fail(); },
              onStateChange: function (e) {
                // 1 = playing; only then reveal the motion (iframe stays invisible otherwise)
                if (e.data === 1) {
                  started = true;
                  if (watchdog) clearTimeout(watchdog);
                  const crop = fig.querySelector(".plate-crop");
                  if (crop) crop.classList.add("is-live");
                  if (skel) skel.classList.add("is-done");
                }
                if (e.data === 0) {
                  try { e.target.seekTo(0); e.target.playVideo(); } catch (err) {}
                }
              },
            },
          });
        } catch (err) {
          fail();
          return;
        }
        ytPlayers[uid] = player;
        // If the impression never actually plays, keep the still and drop the iframe.
        watchdog = setTimeout(function () {
          if (!started) fail();
        }, 6000);
      };
      if (ytReady) boot();
      else ytQueue.push(boot);
      // If the IFrame API never arrives, still keep the poster.
      setTimeout(function () {
        if (!started && fig.getAttribute("data-motion") !== "still") {
          if (!window.YT || !window.YT.Player) fail();
        }
      }, 7000);

      if (btn) {
        btn.addEventListener("click", function () {
          const p = ytPlayers[uid];
          if (!p || fig.getAttribute("data-motion") === "still") {
            openWatch();
            return;
          }
          try {
            const muted = typeof p.isMuted === "function" ? p.isMuted() : true;
            if (muted) {
              p.unMute();
              p.setVolume(80);
              btn.textContent = "Sound on";
              btn.setAttribute("aria-pressed", "true");
              btn.setAttribute("aria-label", "Mute this living plate");
            } else {
              p.mute();
              btn.textContent = "Sound off";
              btn.setAttribute("aria-pressed", "false");
              btn.setAttribute("aria-label", "Unmute this living plate");
            }
          } catch (err) {
            openWatch();
          }
        });
      }
    });
  }


  function isStandalone() {
    return (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches)
      || window.navigator.standalone === true;
  }

  function isIos() {
    return /iphone|ipad|ipod/i.test(window.navigator.userAgent)
      || (window.navigator.platform === "MacIntel" && window.navigator.maxTouchPoints > 1);
  }

  function bindInstall() {
    const root = document.getElementById("keep-paper");
    const btn = document.getElementById("install-edition");
    const ios = document.getElementById("ios-install");
    if (!root) return;
    if (isStandalone()) {
      root.hidden = true;
      return;
    }
    let deferred = null;
    window.addEventListener("beforeinstallprompt", function (e) {
      e.preventDefault();
      deferred = e;
      if (btn) {
        btn.hidden = false;
        root.hidden = false;
      }
    });
    if (btn) {
      btn.addEventListener("click", function () {
        if (!deferred) return;
        deferred.prompt();
        deferred.userChoice.finally(function () {
          deferred = null;
          btn.hidden = true;
        });
      });
    }
    if (isIos() && ios) {
      ios.hidden = false;
      root.hidden = false;
    }
  }

  function bindSeek(ed) {
    const input = document.getElementById("seek-input");
    const box = document.getElementById("seek-results");
    if (!input || !box) return;
    const all = Object.values(ed.stories || {});
    function close() { box.classList.remove("open"); box.innerHTML = ""; }
    input.addEventListener("input", function () {
      const q = input.value.trim().toLowerCase();
      if (q.length < 2) { close(); return; }
      const hits = all.filter(s =>
        (s.headline + " " + (s.deck || "") + " " + s.source + " " + (s.author || "")).toLowerCase().indexOf(q) !== -1
      ).slice(0, 8);
      if (!hits.length) {
        box.classList.add("open");
        box.innerHTML = "<p>No leaf in this edition matches that query.</p>";
        return;
      }
      box.classList.add("open");
      box.innerHTML = hits.map(s =>
        '<a href="' + storyUrl(s.id) + '">' + escapeHtml(s.headline) +
        ' <span class="src">' + escapeHtml(s.source) + " · " + escapeHtml((ed.desks[s.desk] || {}).flag || s.desk) + "</span></a>"
      ).join("");
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { close(); input.blur(); }
      if (e.key === "Enter") {
        const first = box.querySelector("a");
        if (first) { e.preventDefault(); first.click(); }
      }
    });
    document.addEventListener("click", function (e) {
      if (!box.contains(e.target) && e.target !== input) close();
    });
  }

  function inkTrail() {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (window.matchMedia && window.matchMedia("(pointer: coarse)").matches) return;
    const canvas = document.getElementById("ink-trail");
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext("2d");
    const dots = [];
    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);
    let last = 0;
    window.addEventListener("mousemove", function (e) {
      const now = performance.now();
      if (now - last < 24) return;
      last = now;
      dots.push({ x: e.clientX, y: e.clientY, a: 0.18, r: 1.8 });
      if (dots.length > 28) dots.shift();
    });
    function frame() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < dots.length; i++) {
        const d = dots[i];
        ctx.beginPath();
        ctx.fillStyle = "rgba(28,21,14," + d.a + ")";
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fill();
        d.a *= 0.94;
        d.r *= 1.015;
      }
      while (dots.length && dots[0].a < 0.02) dots.shift();
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function boot() {
    const ed = edition();
    if (!ed) return;
    fillChrome(ed);
    const kind = pageKind();
    if (kind === "front") renderFront(ed);
    else if (kind === "section") renderSection(ed);
    else if (kind === "article") renderArticle(ed);
    bindSeek(ed);
    bindInstall();
    mountPlates();
    inkTrail();
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
