#!/usr/bin/env python3
import json, os, socket, random, requests, re, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PORT = int(os.environ.get("PORT", 8000))
HOST = "0.0.0.0"
API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

saved_videos_data = []

def search_youtube(query, max_results=10):
    if not API_KEY: return []
    url = "https://www.googleapis.com/youtube/v3/search"
    # We search for the channel name, order by date to get newest videos,
    # and filter for medium/long videos to avoid Shorts and clickbait.
    params = {
        "part": "snippet", "q": query, "type": "video",
        "maxResults": max_results, "videoEmbeddable": "true",
        "safeSearch": "strict", "relevanceLanguage": "en",
        "videoDuration": "medium", "order": "date", "key": API_KEY,
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        data = r.json()
        videos = []
        for item in data.get("items", []):
            snippet = item["snippet"]
            title = snippet["title"]
            
            # 🚫 STRICT LANGUAGE FILTER: Skip if the title contains Arabic, Urdu, Cyrillic, Chinese, etc.
            # This regex looks for characters in non-Latin Unicode blocks.
            if re.search(r'[\u0600-\u06FF\u0400-\u04FF\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', title):
                continue
                
            videos.append({
                "id": item["id"]["videoId"], "title": title,
                "channel": snippet["channelTitle"], "topic": query.title(),
            })
        return videos
    except Exception as e:
        print(f"Search error: {e}")
        return []

def fetch_ai_feed():
    if not API_KEY: return []
    
    # Your exact subscription list
    CHANNELS = [
        "Gabriel Iglesias", "Throttle House", "Nouman Ali Khan", "Dr. Roy Casagranda",
        "carwow", "Veritasium", "Art Chad", "Papersdock", "Yaqeen Institute",
        "Johnny Harris", "Muslim Founder", "fern", "Mustard", "NullSpace",
        "Real Time History", "Dr Israr Ahmed Official", "Gus Vidales", "Tavarish",
        "Sahil Adeem", "A Simple Argument", "Hamza Yusuf", "OnePath Network",
        "The Thinking Muslim", "Stargaze", "Damon Cassidy", "Let's Explore Our D",
        "Youth Club", "Iman Gadzhi", "Kurzgesagt", "Edmund Yong", "Ustadh Rhyad",
        "How Money Works", "Sammy Obeid"
    ]
    
    # Pick 10 random channels from the list
    selected_channels = random.sample(CHANNELS, 10)
    
    all_videos = []
    for channel in selected_channels:
        # Fetch only 3 videos per channel so the feed stays mixed
        videos = search_youtube(channel, max_results=3)
        all_videos.extend(videos)
        
    # Shuffle everything together so no two videos from the same channel play back-to-back
    random.shuffle(all_videos)
    
    # Remove duplicates (just in case) and return up to 25 videos
    seen = set()
    unique = [v for v in all_videos if v["id"] not in seen and not seen.add(v["id"])]
    return unique[:25]

def get_similar_videos(base_video):
    if not saved_videos_data: return []
    corpus = [f"{v['title']} {v['channel']} {v['topic']}" for v in saved_videos_data]
    corpus.append(f"{base_video['title']} {base_video['channel']} {base_video['topic']}")
    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_features=15)
        tfidf_matrix = vectorizer.fit_transform(corpus)
        cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
        similar_indices = cosine_sim[0].argsort()[-3:][::-1]
        keywords = []
        for idx in similar_indices:
            if cosine_sim[0][idx] > 0.1:
                keywords.extend(saved_videos_data[idx]['title'].split()[:4])
        if keywords:
            query = ' '.join(set(keywords))
            print(f"🤖 ML Recommending based on: {query}")
            return search_youtube(query, 10)
    except Exception as e:
        print(f"ML Error: {e}")
    return []

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#000000">
<title>EduFeed</title>
<style>
  :root { --bg: #000; --text: #fff; --accent: #2dd4bf; --safe-bottom: env(safe-area-inset-bottom, 0px); }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; overflow: hidden; background: var(--bg); }
  body { font-family: -apple-system, sans-serif; color: var(--text); overscroll-behavior: none; touch-action: manipulation; }
  #feed { height: 100dvh; overflow-y: scroll; scroll-snap-type: y mandatory; scrollbar-width: none; }
  #feed::-webkit-scrollbar { display: none; }
  .slide { height: 100dvh; scroll-snap-align: start; scroll-snap-stop: always; position: relative; background: #000; overflow: hidden; }
  .slide iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
  .overlay { position: absolute; inset: 0; pointer-events: none; display: flex; flex-direction: column; justify-content: flex-end; padding: 20px; padding-bottom: calc(20px + var(--safe-bottom)); background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 50%); }
  .meta { pointer-events: auto; max-width: 70%; }
  .topic { font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--accent); margin-bottom: 4px; }
  .title { font-size: 15px; font-weight: 600; line-height: 1.3; margin-bottom: 2px; }
  .channel { font-size: 12px; color: rgba(255,255,255,0.7); }
  .actions { position: absolute; right: 12px; bottom: calc(80px + var(--safe-bottom)); display: flex; flex-direction: column; gap: 20px; pointer-events: auto; }
  .action { background: transparent; border: 0; color: var(--text); cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 4px; font-size: 10px; }
  .action svg { width: 28px; height: 28px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5)); transition: transform 0.1s; }
  .action:active svg { transform: scale(0.85); }
  .action.on svg { color: var(--accent); fill: var(--accent); }
  .unmute-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.7); padding: 14px 22px; border-radius: 50px; font-size: 15px; font-weight: 600; color: white; cursor: pointer; pointer-events: auto; backdrop-filter: blur(8px); z-index: 20; display: flex; align-items: center; gap: 8px; transition: opacity 0.3s; }
  .unmute-overlay:active { transform: translate(-50%, -50%) scale(0.95); }
  .topbar { position: absolute; top: 0; left: 0; right: 0; padding: 16px; display: flex; justify-content: center; pointer-events: none; z-index: 10; }
  .refresh-btn { pointer-events: auto; background: rgba(0,0,0,0.6); backdrop-filter: blur(8px); color: var(--text); border: 1px solid rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: 600; cursor: pointer; }
  .refresh-btn:active { transform: scale(0.95); }
  .loading { height: 100dvh; display: flex; align-items: center; justify-content: center; color: #888; font-size: 14px; }
</style>
</head>
<body>
<div class="topbar"><button class="refresh-btn" onclick="refreshFeed()">🔄 New AI Feed</button></div>
<div id="feed"><div class="loading">Loading AI feed…</div></div>
<script>
const tag = document.createElement('script'); tag.src = "https://www.youtube.com/iframe_api"; document.head.appendChild(tag);
let feedData = [], players = {}, activeIndex = 0;
let savedVideos = new Set(JSON.parse(localStorage.getItem('saved_videos') || '[]'));

async function refreshFeed() {
  const btn = document.querySelector('.refresh-btn');
  btn.textContent = '⏳ Refreshing…';
  try {
    const res = await fetch('/api/feed?t=' + Date.now());
    feedData = await res.json();
    renderFeed();
    btn.textContent = '🔄 New AI Feed';
    document.getElementById('feed').scrollTo(0, 0);
  } catch(e) { btn.textContent = '🔄 New AI Feed'; }
}

async function loadSimilar(videoId) {
  const videoData = feedData.find(v => v.id === videoId);
  if (!videoData) return;
  try {
    const res = await fetch('/api/similar', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(videoData)
    });
    const similar = await res.json();
    if (similar.length > 0) {
      feedData = similar;
      renderFeed();
      document.getElementById('feed').scrollTo(0, 0);
    }
  } catch(e) {}
}

function renderFeed() {
  const root = document.getElementById('feed');
  root.innerHTML = feedData.map((v, i) => `
    <section class="slide" data-index="${i}" data-id="${v.id}" onclick="unmuteCurrent()">
      <div id="player-${i}"></div>
      <div class="overlay">
        <div class="meta">
          <div class="topic">${v.topic}</div>
          <div class="title">${v.title}</div>
          <div class="channel">${v.channel}</div>
        </div>
      </div>
      <div class="actions">
        <button class="action ${savedVideos.has(v.id)?'on':''}" data-save="${v.id}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
          <span>${savedVideos.has(v.id) ? 'More' : 'Save'}</span>
        </button>
      </div>
      <div class="unmute-overlay" onclick="unmuteCurrent()" style="display:none;">🔊 Tap anywhere to Unmute</div>
    </section>
  `).join('');
  if (window.YT && window.YT.Player) initPlayers();
  else window.onYouTubeIframeAPIReady = initPlayers;
  document.querySelectorAll('.slide').forEach(s => observer.observe(s));
}

function initPlayers() {
  feedData.forEach((v, i) => {
    players[i] = new YT.Player(`player-${i}`, {
      videoId: v.id,
      playerVars: { autoplay: 1, mute: 1, controls: 0, playsinline: 1, rel: 0, modestbranding: 1, fs: 0 },
      events: { 
        onReady: (e) => { e.target.mute(); },
        onStateChange: (e) => { if (e.data === YT.PlayerState.ENDED) { e.target.seekTo(0); e.target.playVideo(); } }
      }
    });
  });
}

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const idx = parseInt(entry.target.dataset.index, 10);
    if (idx === activeIndex) return;
    activeIndex = idx;
    Object.entries(players).forEach(([i, p]) => { if (parseInt(i) !== idx) { try { p.pauseVideo(); } catch(e){} } });
    const current = players[idx];
    if (current) { try { current.mute(); current.playVideo(); } catch(e){} }
    document.querySelectorAll('.unmute-overlay').forEach(el => el.style.display = 'none');
    const overlay = entry.target.querySelector('.unmute-overlay');
    if (overlay) overlay.style.display = 'flex';
  });
}, { threshold: 0.6 });

function unmuteCurrent() {
  const current = players[activeIndex];
  if (current && current.isMuted && current.isMuted()) {
    current.unMute();
    current.playVideo(); // Force play just in case
    document.querySelectorAll('.unmute-overlay').forEach(el => el.style.display = 'none');
  }
}

document.addEventListener('click', async (e) => {
  const saveBtn = e.target.closest('[data-save]');
  if (saveBtn) {
    const id = saveBtn.dataset.save;
    const videoData = feedData.find(v => v.id === id);
    
    if (savedVideos.has(id)) {
      loadSimilar(id); // If already saved, clicking again loads ML recommendations
    } else {
      savedVideos.add(id);
      saveBtn.classList.add('on');
      saveBtn.querySelector('span').textContent = 'More';
      localStorage.setItem('saved_videos', JSON.stringify([...savedVideos]));
      try {
        await fetch('/api/save', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(videoData)
        });
      } catch(err) {}
    }
  }
});
refreshFeed();
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ct="application/json"):
        try:
            self.send_response(code); self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(body))); self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError): pass

    def do_GET(self):
        if self.path.startswith("/api/feed"): self._send(200, json.dumps(fetch_ai_feed()).encode())
        elif self.path in ("/", "/index.html"): self._send(200, HTML.encode(), "text/html; charset=utf-8")
        else: self.send_response(404); self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
            if self.path == "/api/save":
                if payload not in saved_videos_data: saved_videos_data.append(payload)
                self._send(200, b'{"ok":true}')
            elif self.path == "/api/similar":
                self._send(200, json.dumps(get_similar_videos(payload)).encode())
            else: self.send_response(404); self.end_headers()
        except Exception as e: self._send(500, json.dumps({"error": str(e)}).encode())

    def log_message(self, *a): pass

if __name__ == "__main__":
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]; s.close()
    except: local_ip = "127.0.0.1"
    print(f"\n✅ EduFeed running!\n🖥️  Mac:   http://localhost:{PORT}\n📱 Phone: http://{local_ip}:{PORT}\n✅ API Key loaded: {'Yes' if API_KEY else 'No'}\n")
    HTTPServer((HOST, PORT), Handler).serve_forever()
