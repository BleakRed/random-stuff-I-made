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

# ===============================
# CONFIG
# ===============================
CHANNEL_HANDLE = "@BleakRedMN"  # YouTube channel handle
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
            "voice": random.choice(voices).id if voices else None
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

video_id = get_live_video_id(CHANNEL_HANDLE)
if not video_id:
    print(f"{RED}❌ No live stream currently for {CHANNEL_HANDLE}.{RESET}")
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

                    print(f"{color}{author}{RESET}: {message}")

                    if author != YOUR_NAME:
                        speak_async(f"{author} says {message}", voice_id)

                time.sleep(REFRESH_INTERVAL)

        except Exception as e:
            print(f"⚠️ Chat connection error: {e}. Reconnecting in 5s...")
            time.sleep(5)
            continue

try:
    run_chat(video_id)
except KeyboardInterrupt:
    print("\n🛑 Stopping chat listener...")
    save_user_settings()
