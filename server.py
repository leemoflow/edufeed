#!/usr/bin/env python3
"""
Educational TikTok-style feed.
Single-purpose: full-screen vertical scroll of educational YouTube videos.
"""
import json, os, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8000
HOST = "127.0.0.1"  # change to 0.0.0.0 to access from phone on same WiFi

# ── Curated educational playlist ──────────────────────────────
# Swap these video IDs with any educational YouTube videos.
# Format: (youtube_video_id, title, channel, topic)
FEED = [
    ("aircAruvnKk", "But what is a neural network?", "3Blue1Brown", "AI"),
    ("5t1T8i0g5J8", "How I Manage My Time", "Ali Abdaal", "Productivity"),
    ("aXb0m7g7m2c", "The Science of Sleep", "Huberman Lab", "Health"),
    ("wjZofJX0v4M", "The Immune System Explained", "Kurzgesagt", "Science"),
    ("8aGhZQkoFbQ", "How to Learn Anything Faster", "Jim Kwik", "Learning"),
    ("Tc0HXbaZrK0", "The Physics of Time", "Veritasium", "Physics"),
    ("0e3GPea1Tyg", "The History of the Entire World", "Bill Wurtz", "History"),
    ("dQw4w9WgXcQ", "Placeholder — replace with a real video", "System", "Misc"),
]

def get_feed():
    return [{"id": v[0], "title": v[1], "channel": v[2], "topic": v[3]} for v in FEED]

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#000000">
<title>Feed</title>
<style>
  :root {
    --bg: #000;
    --text: #fff;
    --text-muted: rgba(255,255,255,0.7);
    --accent: #2dd4bf;
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bottom: env(safe-area-inset-bottom, 0px);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; overflow: hidden; background: var(--bg); }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
    color: var(--text);
    -webkit-font-smoothing: antialiased;
    overscroll-behavior: none;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }

  /* ── The feed viewport ──────────────────────────── */
  #feed {
    height: 100dvh;  /* dynamic viewport — respects mobile browser chrome */
    overflow-y: scroll;
    scroll-snap-type: y mandatory;
    scroll-behavior: smooth;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }
  #feed::-webkit-scrollbar { display: none; }

  /* ── Each video slide ───────────────────────────── */
  .slide {
    height: 100dvh;
    scroll-snap-align: start;
    scroll-snap-stop: always;
    position: relative;
    background: #000;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .slide iframe {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
  }

  /* ── Overlay: title, channel, actions ───────────── */
  .overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 20px;
    padding-bottom: calc(20px + var(--safe-bottom));
    background: linear-gradient(
      to top,
      rgba(0,0,0,0.75) 0%,
      rgba(0,0,0,0.3) 25%,
      transparent 50%
    );
  }
  .meta {
    pointer-events: auto;
    max-width: 75%;
  }
  .topic {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
    margin-bottom: 6px;
  }
  .title {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.35;
    color: var(--text);
    margin-bottom: 4px;
  }
  .channel {
    font-size: 13px;
    color: var(--text-muted);
  }

  /* ── Side action rail (like TikTok) ─────────────── */
  .actions {
    position: absolute;
    right: 16px;
    bottom: calc(80px + var(--safe-bottom));
    display: flex;
    flex-direction: column;
    gap: 20px;
    pointer-events: auto;
  }
  .action {
    background: transparent;
    border: 0;
    color: var(--text);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-family: inherit;
    padding: 4px;
    -webkit-tap-highlight-color: transparent;
  }
  .action svg {
    width: 32px;
    height: 32px;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
  }
  .action:active svg { transform: scale(0.9); }
  .action.on svg { color: var(--accent); fill: var(--accent); }

  /* ── Top bar: muted indicator ───────────────────── */
  .topbar {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    padding: calc(12px + var(--safe-top)) 16px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    pointer-events: none;
    z-index: 10;
  }
  .muted-badge {
    pointer-events: auto;
    background: rgba(0,0,0,0.6);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    color: var(--text);
    border: 1px solid rgba(255,255,255,0.15);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    display: none;
  }
  .muted-badge.show { display: inline-flex; align-items: center; gap: 6px; }

  /* ── Empty/error state ──────────────────────────── */
  .empty {
    height: 100dvh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 32px;
    color: var(--text-muted);
    font-size: 14px;
  }

  /* ── Save toast ─────────────────────────────────── */
  .toast {
    position: fixed;
    bottom: calc(32px + var(--safe-bottom));
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: var(--accent);
    color: #000;
    padding: 12px 20px;
    border-radius: 24px;
    font-size: 13px;
    font-weight: 600;
    opacity: 0;
    transition: all 0.3s;
    pointer-events: none;
    z-index: 100;
  }
  .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
</style>
</head>
<body>

<div id="feed">
  <div class="empty">Loading feed…</div>
</div>

<div class="toast" id="toast"></div>

<script>
// ── Load YouTube IFrame API ─────────────────────────
const tag = document.createElement('script');
tag.src = "https://www.youtube.com/iframe_api";
document.head.appendChild(tag);

// ── State ───────────────────────────────────────────
let feedData = [];
let players = {};       // id → YT.Player instance
let activeIndex = 0;
let isMuted = true;
let savedVideos = new Set(JSON.parse(localStorage.getItem('saved_videos') || '[]'));

// ── Render the feed ─────────────────────────────────
async function loadFeed() {
  const res = await fetch('/api/feed');
  feedData = await res.json();
  const root = document.getElementById('feed');

  if (!feedData.length) {
    root.innerHTML = '<div class="empty">No videos in feed.<br>Add video IDs to <code>FEED</code> in server.py.</div>';
    return;
  }

  root.innerHTML = feedData.map((v, i) => `
    <section class="slide" data-index="${i}" data-id="${v.id}">
      <div id="player-${i}"></div>
      <div class="overlay">
        <div class="meta">
          <div class="topic">${v.topic}</div>
          <div class="title">${v.title}</div>
          <div class="channel">${v.channel}</div>
        </div>
      </div>
      <div class="actions">
        <button class="action" data-save="${v.id}" aria-label="Save video">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
          </svg>
          <span>Save</span>
        </button>
        <button class="action" data-mute aria-label="Toggle sound">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
          </svg>
          <span>Sound</span>
        </button>
      </div>
    </section>
  `).join('');

  // Wait for API, then init players
  if (window.YT && window.YT.Player) {
    initPlayers();
  } else {
    window.onYouTubeIframeAPIReady = initPlayers;
  }
}

// ── Initialize all players ──────────────────────────
function initPlayers() {
  feedData.forEach((v, i) => {
    players[i] = new YT.Player(`player-${i}`, {
      videoId: v.id,
      playerVars: {
        autoplay: 0,
        mute: 1,
        controls: 0,
        modestbranding: 1,
        rel: 0,
        playsinline: 1,
        fs: 0,
        iv_load_policy: 3,
      },
      events: {
        onReady: (e) => { e.target.mute(); },
        onStateChange: (e) => {
          if (e.data === YT.PlayerState.ENDED) {
            // Loop the video (TikTok behavior)
            e.target.seekTo(0);
            e.target.playVideo();
          }
        }
      }
    });
  });
}

// ── Intersection Observer: play visible, pause rest ─
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const idx = parseInt(entry.target.dataset.index, 10);
    if (idx === activeIndex) return;
    activeIndex = idx;

    // Pause all, play current
    Object.entries(players).forEach(([i, p]) => {
      try { p.pauseVideo(); } catch(e) {}
    });
    const current = players[idx];
    if (current) {
      try {
        current.mute();
        current.playVideo();
        // Show muted badge if first time
        if (isMuted) showMutedBadge();
      } catch(e) {}
    }
  });
}, { threshold: 0.6 });

// ── Wire up observers + actions after render ────────
const origLoadFeed = loadFeed;
loadFeed = async function() {
  await origLoadFeed();
  document.querySelectorAll('.slide').forEach(s => observer.observe(s));

  document.querySelectorAll('[data-save]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.save;
      if (savedVideos.has(id)) {
        savedVideos.delete(id);
        btn.classList.remove('on');
        toast('Removed');
      } else {
        savedVideos.add(id);
        btn.classList.add('on');
        toast('Saved');
      }
      localStorage.setItem('saved_videos', JSON.stringify([...savedVideos]));
    });
    if (savedVideos.has(btn.dataset.save)) btn.classList.add('on');
  });

  document.querySelectorAll('[data-mute]').forEach(btn => {
    btn.addEventListener('click', toggleMute);
  });
};

// ── Mute control ────────────────────────────────────
function showMutedBadge() {
  let badge = document.querySelector('.muted-badge');
  if (!badge) {
    badge = document.createElement('button');
    badge.className = 'muted-badge';
    badge.innerHTML = '🔇 Tap for sound';
    badge.onclick = toggleMute;
    document.querySelector('.topbar')?.appendChild(badge) ||
      document.body.appendChild(badge);
  }
  badge.classList.add('show');
}

function toggleMute() {
  isMuted = !isMuted;
  const current = players[activeIndex];
  if (!current) return;
  if (isMuted) {
    current.mute();
  } else {
    current.unMute();
    document.querySelector('.muted-badge')?.classList.remove('show');
  }
}

// ── Toast ───────────────────────────────────────────
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 1500);
}

// ── Add topbar element ──────────────────────────────
const topbar = document.createElement('div');
topbar.className = 'topbar';
document.body.appendChild(topbar);

// ── Boot ────────────────────────────────────────────
loadFeed();
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ct="application/json"):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path == "/api/feed":
            self._send(200, json.dumps(get_feed()).encode())
        elif self.path in ("/", "/index.html"):
            self._send(200, HTML.encode(), "text/html; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"Feed: http://localhost:{PORT}")
    print(f"Phone (same WiFi): http://<your-mac-ip>:{PORT}")
    HTTPServer((HOST, PORT), Handler).serve_forever()
