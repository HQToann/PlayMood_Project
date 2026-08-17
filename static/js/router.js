/* eslint-env browser, es6 */
/* global Promise, fetch, URL, DOMParser, bootstrap */
(function () {
    "use strict";

    // ─── Config ─────────────────────────────────────────────────────────────────
    var EXCLUDED = ["/auth/", "/admin/", "/api/"];
    var INCLUDED = ["/", "/library/", "/playlist/", "/explore/", "/mood/",
                    "/profile/", "/settings/", "/notifications/", "/social/",
                    "/search/", "/song/"];

    // Shell scripts – loaded once, never re-run via AJAX
    var SHELL = [
        "bootstrap.bundle.min.js", "main.js", "player.js",
        "router.js", "sidebar.js", "create_playlist.js",
        "top_header.js"
    ];

    // Prefetch cache: url → Promise<html string>
    var _prefetchCache = {};
    var _navigating = false;

    // ─── Helpers ────────────────────────────────────────────────────────────────
    function shouldIntercept(url) {
        try {
            var p = new URL(url, window.location.origin);
            if (p.origin !== window.location.origin) return false;
            var path = p.pathname;
            for (var i = 0; i < EXCLUDED.length; i++) {
                if (path.startsWith(EXCLUDED[i])) return false;
            }
            for (var j = 0; j < INCLUDED.length; j++) {
                if (path === INCLUDED[j] || path.startsWith(INCLUDED[j])) return true;
            }
            return false;
        } catch (e) { return false; }
    }

    function isShell(src) {
        var fn = src.split("/").pop().split("?")[0];
        for (var i = 0; i < SHELL.length; i++) {
            if (fn === SHELL[i]) return true;
        }
        return false;
    }

    function isExternal(src) {
        try {
            var p = new URL(src, window.location.origin);
            return p.origin !== window.location.origin;
        } catch (e) { return false; }
    }

    /**
     * Fetch a script's source, then execute it with a DOMContentLoaded shim
     * so that scripts using document.addEventListener('DOMContentLoaded', fn)
     * work correctly in AJAX navigation context.
     */
    var _executedScripts = {};
    function fetchAndRun(src) {
        if (_executedScripts[src]) return Promise.resolve();

        return fetch(src, { credentials: "same-origin" , cache: 'no-store'})
            .then(function (r) {
                if (!r.ok) throw new Error("Script fetch failed: " + r.status + " " + src);
                return r.text();
            })
            .then(function (code) {
                _executedScripts[src] = true;
                var s = document.createElement("script");
                // Shim: intercept DOMContentLoaded → fire immediately via setTimeout
                s.textContent =
                    "(function(){\n" +
                    "var _AEL=document.addEventListener;\n" +
                    "document.addEventListener=function(ev,fn,opts){\n" +
                    "  if(ev==='DOMContentLoaded'){setTimeout(fn,0);return;}\n" +
                    "  return _AEL.call(document,ev,fn,opts);\n" +
                    "};\n" +
                    "try{" + code + "\n}finally{document.addEventListener=_AEL;}\n" +
                    "})();\n//# sourceURL=" + src + "\n";
                document.body.appendChild(s);
            })
            .catch(function (e) {
                console.warn("[Router] fetchAndRun failed:", src, e);
            });
    }

    /**
     * Execute external CDN script (not same-origin) — just append <script src>.
     * Cannot be shimmed for DOMContentLoaded, but CDN libs usually don't use it.
     */
    function loadExternalScript(src) {
        return new Promise(function(resolve) {
            // If already loaded, skip
            if (document.querySelector('script[src="' + src + '"]') || _executedScripts[src]) {
                resolve(); return;
            }
            _executedScripts[src] = true;
            var s = document.createElement("script");
            s.src = src;
            s.onload = resolve;
            s.onerror = resolve; // don't block on CDN failure
            document.body.appendChild(s);
        });
    }

    function runInlineScript(code) {
        // Also shim DOMContentLoaded for inline scripts
        var s = document.createElement("script");
        s.textContent =
            "(function(){\n" +
            "var _AEL=document.addEventListener;\n" +
            "document.addEventListener=function(ev,fn,opts){\n" +
            "  if(ev==='DOMContentLoaded'){setTimeout(fn,0);return;}\n" +
            "  return _AEL.call(document,ev,fn,opts);\n" +
            "};\n" +
            "try{" + code + "\n}finally{document.addEventListener=_AEL;}\n" +
            "})();";
        document.body.appendChild(s);
    }

    function updateActive(pathname) {
        document.querySelectorAll(".nav-link-custom").forEach(function (link) {
            var href = link.getAttribute("href");
            if (!href) return;
            var lp = href.split("?")[0];
            var active = lp === pathname ||
                (pathname !== "/" && pathname.startsWith(lp) && lp !== "/");
            link.classList.toggle("active", active);
        });
    }

    // ─── Loader bar ─────────────────────────────────────────────────────────────
    function showLoader() {
        var bar = document.getElementById("pm-nav-loader");
        if (!bar) {
            if (!document.getElementById("pm-loader-style")) {
                var st = document.createElement("style");
                st.id = "pm-loader-style";
                st.textContent = "@keyframes pmLoad{0%{width:5%}80%{width:80%}100%{width:88%}}";
                document.head.appendChild(st);
            }
            bar = document.createElement("div");
            bar.id = "pm-nav-loader";
            bar.style.cssText =
                "position:fixed;top:0;left:0;height:3px;z-index:99999;" +
                "background:linear-gradient(to right,#1db954,#5cffb0);" +
                "border-radius:0 2px 2px 0;display:none;transition:opacity 0.2s;";
            document.body.appendChild(bar);
        }
        bar.style.opacity = "1";
        bar.style.display = "block";
        bar.style.width = "5%";
        bar.style.animation = "pmLoad 0.8s ease forwards";
    }

    function hideLoader() {
        var bar = document.getElementById("pm-nav-loader");
        if (!bar) return;
        bar.style.animation = "none";
        bar.style.width = "100%";
        setTimeout(function () {
            bar.style.opacity = "0";
            setTimeout(function () { bar.style.display = "none"; bar.style.width = "5%"; bar.style.opacity = "1"; }, 200);
        }, 80);
    }

    // ─── Content transition ──────────────────────────────────────────────────────
    function fadeOut(el, cb) {
        el.style.transition = "opacity 0.12s ease";
        el.style.opacity = "0.4";
        setTimeout(cb, 120);
    }

    function fadeIn(el) {
        el.style.opacity = "0.4";
        requestAnimationFrame(function () {
            el.style.transition = "opacity 0.18s ease";
            el.style.opacity = "1";
            setTimeout(function () { el.style.transition = ""; }, 200);
        });
    }

    // ─── Prefetch ────────────────────────────────────────────────────────────────
    function prefetch(url) {
        if (!shouldIntercept(url)) return;
        if (_prefetchCache[url]) return;
        _prefetchCache[url] = fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin"
        })
        .then(function (r) {
            if (!r.ok || !shouldIntercept(r.url)) { delete _prefetchCache[url]; return null; }
            return r.text();
        })
        .catch(function () { delete _prefetchCache[url]; return null; });
    }

    // ─── Core navigate ───────────────────────────────────────────────────────────
    function cleanupBootstrap() {
        if (typeof window.bootstrap !== 'undefined') {
            document.querySelectorAll('.offcanvas.show, .modal.show').forEach(function(el) {
                try {
                    var bsOffcanvas = window.bootstrap.Offcanvas.getInstance(el);
                    if (bsOffcanvas) {
                        el.classList.remove('show');
                        el.style.display = 'none';
                        bsOffcanvas.dispose();
                    }
                    var bsModal = window.bootstrap.Modal.getInstance(el);
                    if (bsModal) {
                        el.classList.remove('show');
                        el.style.display = 'none';
                        bsModal.dispose();
                    }
                } catch(e) {}
            });
        }
        document.querySelectorAll('.offcanvas-backdrop, .modal-backdrop').forEach(function(el) { el.remove(); });
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }

    function navigate(url, push) {
        if (!shouldIntercept(url)) { window.location.href = url; return; }
        if (_navigating) return;
        _navigating = true;

        showLoader();
        cleanupBootstrap();
        
        // Đóng các panel của player (Queue, Devices, Lyrics) để tránh block màn hình
        if (typeof window.closeAllPlayerPanels === 'function') {
            window.closeAllPlayerPanels();
        }

        var currMain = document.querySelector("main.main-content");

        // Start fade-out immediately (don't wait for fetch)
        var fadePromise = new Promise(function (resolve) {
            if (currMain) { fadeOut(currMain, resolve); }
            else { resolve(); }
        });

        // Get HTML — use prefetch cache if available
        var htmlPromise = _prefetchCache[url]
            ? _prefetchCache[url]
            : fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin", cache: "no-store" })
                .then(function (r) {
                    if (!r.ok) throw new Error(r.status);
                    if (!shouldIntercept(r.url)) { window.location.href = r.url; return Promise.reject("redirect"); }
                    return r.text();
                });

        // Delete from cache after use (so re-navigating gets fresh content)
        delete _prefetchCache[url];

        Promise.all([htmlPromise, fadePromise])
            .then(function (results) {
                var html = results[0];
                if (!html) {
                    window.location.href = url;
                    return Promise.reject("redirect");
                }

                var doc = new DOMParser().parseFromString(html, "text/html");
                var newMain = doc.querySelector("main.main-content");
                currMain = document.querySelector("main.main-content");
                if (!newMain || !currMain) { window.location.href = url; return Promise.reject("bad-structure"); }

                // Swap content
                // currMain.innerHTML = newMain.innerHTML;
                
                // Swap Modals and Offcanvas (excluding global ones)
                var globalIds = ["createPlaylistModal", "leftSidebar"];
                var oldOverlays = Array.from(document.querySelectorAll("body > .modal, body > .offcanvas"));
                oldOverlays.forEach(function (m) {
                    if (m.id && globalIds.indexOf(m.id) === -1) {
                        m.remove();
                    }
                });
                var newOverlays = Array.from(doc.querySelectorAll("body > .modal, body > .offcanvas"));
                newOverlays.forEach(function (m) {
                    if (m.id && globalIds.indexOf(m.id) === -1) {
                        document.body.appendChild(m);
                    }
                });

                // Update title
                var t = doc.querySelector("title");
                if (t) document.title = t.textContent;

                // Inject new CSS links
                doc.querySelectorAll("link[rel=stylesheet]").forEach(function (lk) {
                    var fn = lk.href.split("/").pop().split("?")[0];
                    if (!document.querySelector('link[href*="' + fn + '"]')) {
                        document.head.appendChild(lk.cloneNode());
                    }
                });

                // Inject new head <style> blocks (page-specific inline CSS)
                doc.querySelectorAll("head style:not([id])").forEach(function (st) {
                    var clone = document.createElement("style");
                    clone.textContent = st.textContent;
                    document.head.appendChild(clone);
                });

                // Swap content
                currMain.innerHTML = newMain.innerHTML;
                fadeIn(currMain);

                // Run inline scripts inside <main> (e.g. window.ALBUM_CONFIG)
                Array.from(currMain.querySelectorAll("script:not([src])")).forEach(function (s) {
                    runInlineScript(s.textContent);
                });

                // Build a sequential chain to maintain script execution order
                var chain = Promise.resolve();

                // SAFETY-NET: handle script[src] inside <main> from new doc
                // (normally scripts should be in <body>, but some pages may place them inside main)
                Array.from(doc.querySelectorAll("main.main-content script[src]")).forEach(function (script) {
                    var src = script.getAttribute("src");
                    if (!src) return;
                    var fullSrc;
                    try { fullSrc = new URL(src, window.location.origin).href; } catch (e) { return; }
                    var bare = fullSrc.split("?")[0];
                    if (isShell(bare)) return;
                    if (isExternal(fullSrc)) {
                        chain = chain.then(function () { return loadExternalScript(fullSrc); });
                    } else {
                        chain = chain.then(function () { return fetchAndRun(fullSrc); });
                    }
                });

                // Collect body scripts in DOCUMENT ORDER, skip shell scripts
                var bodyScripts = Array.from(doc.querySelectorAll("body > script"));

                // Build sequential chain (continue from main scripts chain)
                bodyScripts.forEach(function (script) {
                    var src = script.getAttribute("src");
                    if (src) {
                        var fullSrc;
                        try { fullSrc = new URL(src, window.location.origin).href; } catch (e) { return; }
                        var bare = fullSrc.split("?")[0];
                        if (isShell(bare)) return; // skip shell
                        if (isExternal(fullSrc)) {
                            // CDN script — load via <script src>
                            chain = chain.then(function () { return loadExternalScript(fullSrc); });
                        } else {
                            // Same-origin page script — fetch+shim
                            chain = chain.then(function () { return fetchAndRun(fullSrc); });
                        }
                    } else {
                        // Inline script (e.g. window.USER_IS_AUTHENTICATED)
                        var code = script.textContent;
                        chain = chain.then(function () { runInlineScript(code); });
                    }
                });

                return chain.then(function() {
                    // Re-init Bootstrap Dropdown
                    if (typeof window.bootstrap !== 'undefined') {
                        document.querySelectorAll('[data-bs-toggle="dropdown"]').forEach(function(el) {
                            try {
                                var existing = bootstrap.Dropdown.getInstance(el);
                                if (existing) existing.dispose();
                                new bootstrap.Dropdown(el);
                            } catch(e) {}
                        });
                        // Re-init Offcanvas
                        document.querySelectorAll('[data-bs-toggle="offcanvas"]').forEach(function(el) {
                            try { new bootstrap.Offcanvas(document.querySelector(el.dataset.bsTarget)); } catch(e) {}
                        });
                    }
                });
            })
            .then(function () {
                // Scroll to top
                var sc = document.querySelector("main.main-content .content-scroll");
                if (sc) sc.scrollTop = 0;
                if (push) history.pushState({ url: url }, "", url);
                updateActive(new URL(url, window.location.origin).pathname);
            })
            .catch(function (err) {
                if (currMain) currMain.style.opacity = "1";
                if (err !== "redirect" && err !== "bad-structure") {
                    console.warn("[Router] fallback:", err);
                    window.location.href = url;
                }
            })
            .finally(function () {
                hideLoader();
                _navigating = false;
            });
    }

    // ─── Events ──────────────────────────────────────────────────────────────────

    // Click: intercept nav links
    document.addEventListener("click", function (e) {
        var link = e.target.closest("a[href]");
        if (!link) return;
        var href = link.getAttribute("href");
        if (!href || link.target === "_blank" || link.hasAttribute("download")) return;
        if (href.indexOf("javascript") === 0 || href.indexOf("#") === 0 ||
            href.indexOf("mailto:") === 0 || href.indexOf("tel:") === 0) return;
        var fullUrl;
        try { fullUrl = new URL(href, window.location.origin).href; } catch (e2) { return; }
        if (!shouldIntercept(fullUrl) || fullUrl === window.location.href) return;
        e.preventDefault();
        navigate(fullUrl, true);
    });

    // Hover: prefetch to reduce perceived latency
    document.addEventListener("mouseover", function (e) {
        var link = e.target.closest("a[href]");
        if (!link) return;
        var href = link.getAttribute("href");
        if (!href || href.indexOf("javascript") === 0 || href.indexOf("#") === 0) return;
        var fullUrl;
        try { fullUrl = new URL(href, window.location.origin).href; } catch (e2) { return; }
        if (fullUrl !== window.location.href) prefetch(fullUrl);
    });

    // Back/Forward
    window.addEventListener("popstate", function (e) {
        navigate(e.state && e.state.url ? e.state.url : window.location.href, false);
    });

    // Push initial state so popstate works for first page
    history.replaceState({ url: window.location.href }, "", window.location.href);

    window.pmNavigate = navigate;
    window.pmPrefetch  = prefetch;
})();
