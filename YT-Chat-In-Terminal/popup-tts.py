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

# ===============================
# CONFIG
# ===============================
CHANNEL_HANDLE = "@TheVtuberCh"
REFRESH_INTERVAL = 5
YOUR_NAME = "Me"
SETTINGS_FILE = "user_settings.json"

# ===============================
# Terminal Colors
# ===============================
RESET = "\033[0m"
COLORS = ["\033[31m", "\033[32m", "\033[34m", "\033[36m", "\033[33m", "\033[35m"]

# ===============================
# Flask Overlay Setup
# ===============================
app = Flask(__name__)
chat_history = []
current_tts = {"author": "", "message": ""}


@app.route("/")
def overlay():
    html = """
    <html>
    <head>
    <meta http-equiv="refresh" content="1">
    <style>
        body {
            background: transparent;
            color: white;
            font-family: Arial, sans-serif;
            font-size: 20px;
            overflow: hidden;
        }
        .chatline {
            margin-bottom: 4px;
        }
        .tts {
            color: yellow;
            font-weight: bold;
            text-shadow: 0 0 10px yellow;
            animation: fade 2s ease-out;
        }
        @keyframes fade {
            0% {opacity: 1;}
            100% {opacity: 0;}
        }
    </style>
    </head>
    <body>
        {% for line in chat %}
            <div class="chatline">{{ line }}</div>
        {% endfor %}
        {% if tts.author %}
            <div class="tts">{{ tts.author }} says {{ tts.message }}</div>
        {% endif %}
    </body>
    </html>
    """
    return render_template_string(html, chat=chat_history[-10:], tts=current_tts)


# Run Flask server in a thread
def run_overlay():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


threading.Thread(target=run_overlay, daemon=True).start()

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
        text, voice_id, author = tts_queue.get()
        if text is None:
            break
        try:
            current_tts["author"] = author
            current_tts["message"] = text
            tts_engine.setProperty("voice", voice_id)
            tts_engine.say(text)
            tts_engine.runAndWait()
            current_tts["author"] = ""
            current_tts["message"] = ""
        except Exception as e:
            print(f"TTS error: {e}")
        tts_queue.task_done()


threading.Thread(target=tts_worker, daemon=True).start()


def speak_async(text, voice_id, author):
    tts_queue.put((text, voice_id, author))


# ===============================
# Persistent User Settings
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
# YouTube Live ID Fetcher
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


video_id = get_live_video_id(CHANNEL_HANDLE)
if not video_id:
    print(f"\033[31m❌ No live stream currently for {CHANNEL_HANDLE}.\033[0m")
    sys.exit(1)

print(f"✅ Live video ID: {video_id}")


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

                    line = f"{author}: {message}"
                    print(f"{color}{line}{RESET}")
                    chat_history.append(line)

                    if author != YOUR_NAME:
                        speak_async(message, voice_id, author)
                time.sleep(REFRESH_INTERVAL)
        except Exception as e:
            print(f"⚠️ Chat connection error: {e}. Reconnecting in 5s...")
            time.sleep(5)


try:
    run_chat(video_id)
except KeyboardInterrupt:
    print("\n🛑 Stopping chat listener...")
    save_user_settings()
