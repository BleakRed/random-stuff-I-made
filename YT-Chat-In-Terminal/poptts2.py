import pyttsx3
import pytchat
import threading
import queue
import time
import requests
import re
import sys
import json
import os
import random
from flask import Flask, render_template_string, jsonify
import webview

# ===============================
# CONFIG
# ===============================
CHANNEL_HANDLE = "@TheVtuberCh"  # YouTube channel handle
REFRESH_INTERVAL = 5  # seconds between checking new messages
YOUR_NAME = "Me"  # Replace with your YouTube display name
SETTINGS_FILE = "user_settings.json"

# ===============================
# ANSI Colors for terminal
# ===============================
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BOLD = "\033[1m"
COLORS = [RED, GREEN, BLUE, CYAN, YELLOW, MAGENTA]

# ===============================
# Flask App for Overlay
# ===============================
app = Flask(__name__)
chat_display = []  # will store last messages for overlay


@app.route("/")
def index():
    html = """
    <html>
    <head>
        <style>
            body {
                background: rgba(0,0,0,0);
                margin: 0;
                padding: 10px;
                color: white;
                font-family: 'Segoe UI', sans-serif;
                overflow: hidden;
            }
            .msg {
                margin: 3px 0;
                font-size: 16px;
                text-shadow: 2px 2px 4px black;
            }
            .author {
                font-weight: bold;
                margin-right: 5px;
            }
        </style>
        <script>
        async function updateChat() {
            const res = await fetch("/data");
            const data = await res.json();
            const container = document.getElementById("chat");
            container.innerHTML = "";
            data.forEach(msg => {
                const div = document.createElement("div");
                div.className = "msg";
                div.innerHTML = `<span class="author" style="color:${msg.color}">${msg.author}:</span> ${msg.message}`;
                container.appendChild(div);
            });
        }
        setInterval(updateChat, 1000);
        </script>
    </head>
    <body>
        <div id="chat"></div>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route("/data")
def data():
    return jsonify(chat_display[-10:])  # show last 10 messages


# ===============================
# TTS Setup
# ===============================
tts_engine = pyttsx3.init()
voices = tts_engine.getProperty("voices")
tts_engine.setProperty("rate", 150)
tts_engine.setProperty("volume", 0.8)
tts_queue = queue.Queue()


def tts_worker():
    while True:
        text, voice_id = tts_queue.get()
        if text is None:
            break
        try:
            tts_engine.setProperty("voice", voice_id)
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")
        tts_queue.task_done()


threading.Thread(target=tts_worker, daemon=True).start()


def speak_async(text, voice_id):
    tts_queue.put((text, voice_id))


# ===============================
# User Settings (Persistent)
# ===============================
def load_user_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_user_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(user_settings, f)


user_settings = load_user_settings()


def get_user_settings(username):
    if username not in user_settings:
        user_settings[username] = {
            "color": random.choice(COLORS),
            "voice": random.choice(voices).id if voices else None,
        }
        save_user_settings()
    return user_settings[username]


# ===============================
# Scrape live video ID
# ===============================
def get_live_video_id(channel_handle: str) -> str:
    url = f"https://www.youtube.com/{channel_handle}/live"
    resp = requests.get(url)
    if '"isLiveNow":true' not in resp.text:
        return None
    match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
    if match:
        return match.group(1)
    return None


# ===============================
# Chat Reader
# ===============================
def run_chat(video_id):
    processed_messages = set()
    print(f"🎧 Listening to live chat for {CHANNEL_HANDLE}...\n")

    while True:
        try:
            chat = pytchat.create(video_id=video_id)

            while chat.is_alive():
                for c in chat.get().sync_items():
                    msg_id = c.id
                    if msg_id in processed_messages:
                        continue
                    processed_messages.add(msg_id)

                    author = c.author.name
                    message = c.message

                    settings = get_user_settings(author)
                    color = settings["color"]
                    voice_id = settings["voice"]

                    print(f"{color}{author}{RESET}: {message}")

                    chat_display.append(
                        {
                            "author": author,
                            "message": message,
                            "color": color.replace(
                                "\033", "#"
                            ),  # just to ensure valid CSS color
                        }
                    )

                    if author != YOUR_NAME:
                        speak_async(f"{author} says {message}", voice_id)

                time.sleep(REFRESH_INTERVAL)

        except Exception as e:
            print(f"⚠️ Chat connection error: {e}. Reconnecting in 5s...")
            time.sleep(5)
            continue


# ===============================
# Overlay Runner (Flask + Webview)
# ===============================
def run_overlay():
    def start_flask():
        app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=False)

    threading.Thread(target=start_flask, daemon=True).start()
    time.sleep(1)
    webview.create_window(
        "Chat Overlay",
        "http://127.0.0.1:5050",
        frameless=True,
        transparent=True,
        width=500,
        height=400,
        easy_drag=True,
        on_top=True,
    )
    webview.start()


# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    video_id = get_live_video_id(CHANNEL_HANDLE)
    if not video_id:
        print(f"{RED}❌ No live stream currently for {CHANNEL_HANDLE}.{RESET}")
        sys.exit(1)

    print(f"✅ Live video ID: {video_id}")

    threading.Thread(target=run_chat, args=(video_id,), daemon=True).start()

    run_overlay()
