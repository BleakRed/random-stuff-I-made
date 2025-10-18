import pytchat
import threading
import time
from flask import Flask, render_template_string
from collections import deque
import requests
import re
import sys

# ======================================
# CONFIGURATION
# ======================================
CHANNEL_HANDLE = "@TheVtuberCh"  # Your YouTube channel handle
REFRESH_INTERVAL = 5  # seconds between chat fetches
MAX_MESSAGES = 20  # number of messages to show in overlay

# ======================================
# Flask overlay setup
# ======================================
app = Flask(__name__)
chat_history = deque(maxlen=MAX_MESSAGES)

# HTML + CSS overlay (for OBS)
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Live Chat Overlay</title>
<style>
body {
  background: transparent;
  color: white;
  font-family: "JetBrains Mono", monospace;
  overflow: hidden;
  margin: 0;
  padding: 10px;
  font-size: 18px;
}
.chat {
  background: rgba(0,0,0,0.45);
  border-radius: 12px;
  padding: 12px;
  max-width: 700px;
}
.msg {
  margin-bottom: 8px;
  animation: fadein 0.3s ease-in;
}
.author {
  font-weight: bold;
  color: #4dd0e1;
}
@keyframes fadein {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
<meta http-equiv="refresh" content="1">
</head>
<body>
<div class="chat">
  {% for author, message in messages %}
    <div class="msg"><span class="author">{{ author }}:</span> {{ message }}</div>
  {% endfor %}
</div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE, messages=list(chat_history))


# ======================================
# YouTube Live Video Fetcher
# ======================================
def get_live_video_id(channel_handle: str) -> str:
    """Fetch the currently live video ID for the channel."""
    url = f"https://www.youtube.com/{channel_handle}/live"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if '"isLiveNow":true' not in resp.text:
        return None
    match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
    if match:
        return match.group(1)
    return None


# ======================================
# YouTube Chat Listener
# ======================================
def chat_listener(video_id: str):
    print(f"🎧 Listening to live chat for video: {video_id}")
    processed = set()
    while True:
        try:
            chat = pytchat.create(video_id=video_id)
            while chat.is_alive():
                for c in chat.get().sync_items():
                    if c.id in processed:
                        continue
                    processed.add(c.id)
                    author, message = c.author.name, c.message
                    chat_history.append((author, message))
                    print(f"{author}: {message}")
                time.sleep(REFRESH_INTERVAL)
        except Exception as e:
            print(f"⚠️ Chat connection error: {e}. Retrying in 5s...")
            time.sleep(5)


# ======================================
# Main Runner
# ======================================
if __name__ == "__main__":
    print("🔍 Fetching live video ID...")
    video_id = get_live_video_id(CHANNEL_HANDLE)
    if not video_id:
        print(f"❌ No active live stream for {CHANNEL_HANDLE}")
        sys.exit(1)

    print(f"✅ Live video ID: {video_id}")
    thread = threading.Thread(target=chat_listener, args=(video_id,), daemon=True)
    thread.start()

    print("🌐 Flask overlay running at: http://127.0.0.1:5050")
    print("🟢 Open this URL in Firefox and capture it via OBS (Window Capture).")
    app.run(host="0.0.0.0", port=5050)
