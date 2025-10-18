import tkinter as tk
import threading
import queue
import time
import pyttsx3
import pytchat
import random
import requests
import re
import sys
import json
import os

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
ANSI_COLORS = {
    "red": "\033[31m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "yellow": "\033[33m",
    "magenta": "\033[35m",
    "orange": "\033[91m",
}
RESET = "\033[0m"
USER_COLORS = list(ANSI_COLORS.keys())

# ===============================
# Load/Save User Settings
# ===============================
def load_user_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(user_settings, f, indent=2)

user_settings = load_user_settings()

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
        text, author, label = tts_queue.get()
        if text is None:
            break
        try:
            voice_id = user_settings[author]["voice"]
            tts_engine.setProperty("voice", voice_id)
            tts_engine.say(f"{author} says {text}")
            tts_engine.runAndWait()
            # Remove label from overlay after speaking
            label.destroy()
            chat_labels.remove(label)
        except Exception as e:
            print(f"TTS error: {e}")
        tts_queue.task_done()

threading.Thread(target=tts_worker, daemon=True).start()

def speak_async(text, author, label):
    tts_queue.put((text, author, label))

# ===============================
# Tkinter Overlay Setup
# ===============================
root = tk.Tk()
root.title("YT Chat Overlay")
root.configure(bg="green")  # OBS chroma key
root.attributes("-topmost", True)
root.geometry("400x600")

chat_frame = tk.Frame(root, bg="green")
chat_frame.pack(fill=tk.BOTH, expand=True)

chat_labels = []

def add_chat_line(author, message):
    """Add chat line to overlay safely from any thread."""
    def _add():
        if author not in user_settings:
            # Assign random color and voice
            user_settings[author] = {
                "color": random.choice(USER_COLORS),
                "voice": random.choice(voices).id if voices else None,
            }
            save_user_settings()

        color_name = user_settings[author].get("color", "white")
        if color_name not in USER_COLORS:
            color_name = "white"

        label = tk.Label(chat_frame, text=f"{author}: {message}", fg=color_name,
                        bg="#222222", bd=2, relief=tk.RIDGE, anchor="w", justify="left",
                        wraplength=380)
        label.pack(fill=tk.X, pady=2, padx=5)
        chat_labels.append(label)
        return label


    # Schedule on main thread and return the label object
    result = queue.Queue()
    def wrapper():
        result.put(_add())
    root.after(0, wrapper)
    return result.get()

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

VIDEO_ID = get_live_video_id(CHANNEL_HANDLE)
if not VIDEO_ID:
    print("❌ No live stream.")
    sys.exit(1)
print(f"✅ Listening to video ID: {VIDEO_ID}")

# ===============================
# Chat Reader
# ===============================
def read_chat():
    processed_messages = set()
    try:
        chat = pytchat.create(video_id=VIDEO_ID, interruptable=False)
    except Exception as e:
        print(f"Failed to start chat: {e}")
        return

    while True:
        try:
            for c in chat.get().sync_items():
                if c.id in processed_messages:
                    continue
                processed_messages.add(c.id)

                # Assign color for terminal from user settings
                if c.author.name not in user_settings:
                    user_settings[c.author.name] = {
                        "color": random.choice(USER_COLORS),
                        "voice": random.choice(voices).id if voices else None,
                    }
                    save_user_settings()

                color_name = user_settings[c.author.name]["color"]
                ansi_color = ANSI_COLORS.get(color_name, "\033[37m")
                print(f"{ansi_color}{c.author.name}: {c.message}{RESET}")

                # Add overlay label
                label = add_chat_line(c.author.name, c.message)

                if c.author.name != YOUR_NAME:
                    speak_async(c.message, c.author.name, label)

            time.sleep(REFRESH_INTERVAL)
        except Exception as e:
            print(f"Chat error: {e}")
            time.sleep(5)

# ===============================
# Start chat
# ===============================
threading.Thread(target=read_chat, daemon=True).start()

root.mainloop()
