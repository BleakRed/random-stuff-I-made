# this is just a Read Only Version

import pyttsx3
import pytchat
import threading
import queue
import time
import requests
import re

# ===============================
# CONFIG
# ===============================
CHANNEL_HANDLE = "@thevtuberch"  # YouTube channel handle
REFRESH_INTERVAL = 1             # seconds between checking new messages
MAX_LENGTH = 200                 # max message length for sending (optional)
YOUR_NAME = "Me"                 # Replace with your YouTube display name

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


def color_name(name: str) -> str:
    colors = [RED, GREEN, BLUE, CYAN, YELLOW, MAGENTA]
    return colors[hash(name) % len(colors)]


# ===============================
# TTS Setup
# ===============================
tts_engine = pyttsx3.init()
tts_engine.setProperty("voice", "gmw/en-us")  # Your preferred voice
tts_engine.setProperty("rate", 150)
tts_engine.setProperty("volume", 1.0)

tts_queue = queue.Queue()


def tts_worker():
    while True:
        text = tts_queue.get()
        if text is None:
            break
        try:
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")
        tts_queue.task_done()


threading.Thread(target=tts_worker, daemon=True).start()


def speak_async(text):
    tts_queue.put(text)

# ===============================
# Scrape live video ID from channel handle
# ===============================


def get_live_video_id(channel_handle: str) -> str:
    url = f"https://www.youtube.com/{channel_handle}/live"
    resp = requests.get(url)
    # Look for "videoId":"XXXXXX" in the page HTML
    match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
    if match:
        return match.group(1)
    else:
        raise Exception(f"No live video currently for {channel_handle}.")


video_id = get_live_video_id(CHANNEL_HANDLE)
print(f"Live video ID: {video_id}")

# ===============================
# Start live chat
# ===============================
chat = pytchat.create(video_id=video_id)
processed_messages = set()

print(f"Listening to live chat for {CHANNEL_HANDLE}...\n")

# ===============================
# Read messages loop
# ===============================
try:
    while chat.is_alive():
        for c in chat.get().sync_items():
            msg_id = c.id
            if msg_id in processed_messages:
                continue
            processed_messages.add(msg_id)

            author = c.author.name
            message = c.message

            # Color based on type
            author_type = c.author.type  # "owner", "moderator", "verified", "member", "default"
            if author_type == "owner":
                color = BOLD + RED
            elif author_type == "moderator":
                color = BOLD + BLUE
            elif author_type == "verified":
                color = GREEN
            else:
                color = color_name(author)

            print(f"{color}{author}{RESET}: {message}")

            # TTS for others
            if author != YOUR_NAME:
                speak_async(f"{author} says {message}")

        time.sleep(REFRESH_INTERVAL)

except KeyboardInterrupt:
    print("\nStopping chat listener...")
    chat.terminate()
