import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import time

# Step 1: Auth
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


creds = None
if os.path.exists("token.json"):
    # load existing token
    with open("token.json", "rb") as token:
        creds = pickle.load(token)

# if no creds or expired, refresh/login
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
    # save creds for next time
    with open("token.json", "wb") as token:
        pickle.dump(creds, token)

youtube = build("youtube", "v3", credentials=creds)


# ANSI Colors
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BOLD = "\033[1m"


def color_name(name: str) -> str:
    """Pick a consistent color based on author name"""
    colors = [RED, GREEN, BLUE, CYAN, YELLOW, MAGENTA]
    return colors[hash(name) % len(colors)]


# Step 2: Get Live Chat ID
video_id = "abcdEFGjkg"  # change this

video_response = (
    youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
)

if not video_response["items"]:
    print("❌ No live video found for this ID. Is it live?")
    exit()

live_chat_id = video_response["items"][0]["liveStreamingDetails"]["activeLiveChatId"]
print(f"Live chat ID: {live_chat_id}")


# Step 3: Read messages in loop
def read_chat():
    request = youtube.liveChatMessages().list(
        liveChatId=live_chat_id, part="snippet,authorDetails"
    )
    response = request.execute()

    for item in response["items"]:
        author = item["authorDetails"]["displayName"]
        message = item["snippet"]["displayMessage"]

        if item["authorDetails"]["isChatOwner"]:
            color = BOLD + RED
        elif item["authorDetails"]["isChatModerator"]:
            color = BOLD + BLUE
        elif item["authorDetails"]["isChatSponsor"]:
            color = GREEN
        else:
            color = color_name(author)

        print(f"{color}{author}{RESET}: {message}")


# Step 4: Send a message

MAX_LENGTH = 200  # YouTube live chat limit


def send_message(text):
    if len(text) > MAX_LENGTH:
        print(f"❌ Message too long ({len(text)} chars). Limit is {MAX_LENGTH}.")
        return

    youtube.liveChatMessages().insert(
        part="snippet",
        body={
            "snippet": {
                "liveChatId": live_chat_id,
                "type": "textMessageEvent",
                "textMessageDetails": {"messageText": text},
            }
        },
    ).execute()


# Example loop
while True:
    read_chat()
    cmd = input(f"Type a message (max {MAX_LENGTH} chars, leave blank to refresh): ")
    if cmd:
        send_message(cmd)
        print(f"{BOLD}{CYAN}Me{RESET}: {cmd}")
    time.sleep(5)
