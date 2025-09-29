import os
import sys
import json
import time
import asyncio
import websockets
import random
import platform
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from colorama import init, Fore, Style
from pyfiglet import Figlet
from ascii_magic import AsciiArt

init(autoreset=True)

ACHECK_FILENAME = "A.CHECK"
FALLBACK_RAW = "https://pastebin.com/raw/zsZNjiwD"

def show_error_message(message, title="Error"):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"{Fore.RED}[ERROR] {message}{Style.RESET_ALL}")
    sys.exit(1)

def print_made_by():
    try:
        f = Figlet(font='slant')
        print(f"{Fore.MAGENTA}{f.renderText('Made by b8lz')}{Style.RESET_ALL}")
    except Exception:
        print(f"{Fore.MAGENTA}Made by b8lz{Style.RESET_ALL}")

def ensure_a_check_file(filename: str = ACHECK_FILENAME, default_url: str = FALLBACK_RAW):
    if os.path.isfile(filename):
        return
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"PASTEBIN_RAW_URL:{default_url}\n")
        print(f"{Fore.GREEN}[INFO] Created {filename} with default Pastebin raw URL.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}[WARN] Could not create {filename}: {e}{Style.RESET_ALL}")

def read_paste_url_from_a_check(filename: str = ACHECK_FILENAME) -> str:
    if not os.path.isfile(filename):
        return ""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("PASTEBIN_RAW_URL:"):
                    return line.split(":", 1)[1].strip()
        return ""
    except Exception:
        return ""

def compute_sha256_of_text_normalized(text: str) -> str:
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    h = hashlib.sha256()
    h.update(normalized.encode('utf-8'))
    return h.hexdigest()

def compute_sha256_of_file(path: str) -> str:
    with open(path, 'rb') as f:
        content = f.read()
    try:
        text = content.decode('utf-8')
        normalized = text.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
        h = hashlib.sha256()
        h.update(normalized)
        return h.hexdigest()
    except Exception:
        h = hashlib.sha256()
        h.update(content)
        return h.hexdigest()

def fetch_text_from_url(url: str, timeout: int = 10) -> str:
    try:
        import requests
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception:
        try:
            from urllib.request import urlopen, Request
            req = Request(url, headers={'User -Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=timeout) as r:
                raw = r.read()
                return raw.decode('utf-8', errors='ignore')
        except Exception as e:
            raise RuntimeError(f"Failed to fetch URL: {e}")

def verify_integrity_using_a_check(script_path: str, a_check_filename: str = ACHECK_FILENAME):
    ensure_a_check_file(a_check_filename, FALLBACK_RAW)
    paste_url = read_paste_url_from_a_check(a_check_filename)
    if not paste_url:
        show_error_message(f"A.CHECK found but no valid 'PASTEBIN_RAW_URL:' line present in {a_check_filename}.")
    try:
        remote_text = fetch_text_from_url(paste_url)
    except Exception as e:
        show_error_message(f"Failed to fetch remote reference from {paste_url}: {e}")
    remote_hash = compute_sha256_of_text_normalized(remote_text)
    local_hash = compute_sha256_of_file(script_path)
    if remote_hash != local_hash:
        # Auto-delete the script and related files if integrity check fails
        files_to_delete = [
            script_path,
            os.path.join(os.path.dirname(script_path), "keep_alive.py"),
            os.path.join(os.path.dirname(script_path), "README.MD"),
            os.path.join(os.path.dirname(script_path), "requirements.txt"),
            os.path.join(os.path.dirname(script_path), "install.bat"),
            os.path.join(os.path.dirname(script_path), ACHECK_FILENAME),
            os.path.join(os.path.dirname(script_path), ".env"),
        ]
        for file_path in files_to_delete:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"{Fore.YELLOW}[INFO] Deleted file: {file_path}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}[ERROR] Failed to delete {file_path}: {e}{Style.RESET_ALL}")
        print(f"{Fore.RED}[ERROR] Integrity check failed. All specified files have been deleted.{Style.RESET_ALL}")
        sys.exit(1)
    else:
        print(f"{Fore.GREEN}[OK] Integrity check passed. Continuing...{Style.RESET_ALL}")

script_file_path = os.path.abspath(__file__) if '__file__' in globals() else os.path.abspath(sys.argv[0])
verify_integrity_using_a_check(script_file_path, ACHECK_FILENAME)

load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    show_error_message("Please add your Discord token to the .env file and restart the application.")

TOKEN = TOKEN.strip('\"\'')
if not TOKEN:
    show_error_message("The TOKEN in your .env file is empty. Please add your Discord token.")

CONFIG = {
    "status": os.getenv("DISCORD_STATUS", "dnd").lower(),
    "guild_id": int(os.getenv("GUILD_ID", "0")),
    "channel_id": int(os.getenv("CHANNEL_ID", "0")),
    "self_mute": os.getenv("SELF_MUTE", "True").lower() == 'true',
    "self_deaf": os.getenv("SELF_DEAF", "False").lower() == 'true',
    "heartbeat_timeout": 5.0,
    "reconnect_delay": 5
}

if not CONFIG["guild_id"] or not CONFIG["channel_id"]:
    print(f"{Fore.RED}[ERROR] Please set GUILD_ID and CHANNEL_ID in your .env file.")
    sys.exit(1)

class VoiceConnector:
    def __init__(self):
        self.websocket = None
        self.heartbeat_task = None
        self.session_id = None
        self.sequence = None
        self.username = "User "
        self.discriminator = "0000"
        self.user_id = "0"
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10

    async def display_banner(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.CYAN}{'='*50}")
        print(f"Voice Connector - Stay In VC 24/7")
        print(f"{Fore.MAGENTA}Made by b8lz")
        print(f"{'='*50}{Style.RESET_ALL}\n")
    
    async def print_status(self, message, status_type="info"):
        colors = {
            "info": Fore.CYAN,
            "success": Fore.GREEN,
            "warning": Fore.YELLOW,
            "error": Fore.RED
        }
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = colors.get(status_type, Fore.WHITE)
        print(f"[{timestamp}] {message}")

    async def animate_connecting(self):
        for _ in range(3):
            for char in '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏':
                sys.stdout.write(f"\r{Fore.CYAN}Connecting {char}")
                sys.stdout.flush()
                await asyncio.sleep(0.1)

    async def send_heartbeats(self, interval):
        try:
            while True:
                await asyncio.sleep(interval)
                try:
                    if self.websocket and self.websocket.open:
                        await self.websocket.send(json.dumps({"op": 1, "d": self.sequence}))
                except Exception as e:
                    await self.print_status(f"Error sending heartbeat: {e}", "error")
                    raise
        except asyncio.CancelledError:
            return
        except Exception as e:
            await self.print_status(f"Heartbeat error: {e}", "error")

    async def connect_to_voice(self):
        uri = 'wss://gateway.discord.gg/?v=9&encoding=json'
        while True:
            try:
                self.connected = False
                await self.display_banner()
                await self.animate_connecting()
                async with websockets.connect(uri, max_size=None) as self.websocket:
                    await self.print_status("WebSocket connection established", "success")
                    hello = json.loads(await self.websocket.recv())
                    heartbeat_interval = hello['d']['heartbeat_interval'] / 1000
                    identify = {
                        "op": 2,
                        "d": {
                            "token": TOKEN,
                            "properties": {
                                "$os": platform.system().lower(),
                                "$browser": "voice_connector",
                                "$device": "voice_connector"
                            },
                            "presence": {
                                "status": CONFIG["status"],
                                "afk": False
                            },
                            "compress": False,
                            "intents": 0
                        }
                    }
                    await self.websocket.send(json.dumps(identify))
                    await self.print_status("Sent identify payload", "success")
                    self.heartbeat_task = asyncio.create_task(
                        self.send_heartbeats(heartbeat_interval)
                    )
                    voice_state = {
                        "op": 4,
                        "d": {
                            "guild_id": str(CONFIG["guild_id"]),
                            "channel_id": str(CONFIG["channel_id"]),
                            "self_mute": CONFIG["self_mute"],
                            "self_deaf": CONFIG["self_deaf"]
                        }
                    }
                    await self.websocket.send(json.dumps(voice_state))
                    await self.print_status("Sent voice state update", "success")
                    self.connected = True
                    self.reconnect_attempts = 0
                    await self.display_banner()
                    while True:
                        try:
                            message = await asyncio.wait_for(
                                self.websocket.recv(),
                                timeout=heartbeat_interval + CONFIG["heartbeat_timeout"]
                            )
                            data = json.loads(message)
                            self.sequence = data.get('s', self.sequence)
                            if data['op'] == 11:  
                                continue
                            elif data['op'] == 9:  
                                await self.print_status("Invalid session, reconnecting...", "warning")
                                await asyncio.sleep(CONFIG["reconnect_delay"])
                                break
                            if data.get('t') == 'READY':
                                user = data['d'].get('user', {})
                                self.username = user.get('username', self.username)
                                self.discriminator = user.get('discriminator', self.discriminator)
                                self.user_id = user.get('id', self.user_id)
                                await self.display_banner()
                                await self.print_status(f"Logged in as {self.username}#{self.discriminator}", "success")
                        except asyncio.TimeoutError:
                            await self.print_status("Connection timeout, reconnecting...", "warning")
                            break
            except (websockets.exceptions.ConnectionClosed, websockets.ConnectionClosed) as e:
                self.connected = False
                self.reconnect_attempts += 1
                await self.display_banner()
                if self.reconnect_attempts > self.max_reconnect_attempts:
                    await self.print_status("Max reconnection attempts reached. Please check your connection and try again.", "error")
                    return
                retry_in = min(CONFIG["reconnect_delay"] * (2 ** (self.reconnect_attempts - 1)), 300)  
                await self.print_status(f"Connection closed: {e}. Reconnecting in {retry_in} seconds...", "error")
                await asyncio.sleep(retry_in)
            except Exception as e:
                self.connected = False
                self.reconnect_attempts += 1
                await self.display_banner()
                await self.print_status(f"Error: {e}", "error")
                await asyncio.sleep(CONFIG["reconnect_delay"])
            finally:
                if self.heartbeat_task and not self.heartbeat_task.done():
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass

    async def run(self):
        try:
            await self.connect_to_voice()
        except KeyboardInterrupt:
            await self.print_status("Shutting down...", "info")
        except Exception as e:
            await self.print_status(f"Fatal error: {e}", "error")
            await self.print_status("Restarting in 30 seconds...", "warning")
            await asyncio.sleep(30)
            await self.run()

def install_requirements():
    requirements = [
        'websockets==10.4',
        'python-dotenv',
        'colorama',
        'pyfiglet',
        'ascii-magic'
    ]
    import subprocess
    import sys
    print(f"{Fore.YELLOW}Installing required packages...{Style.RESET_ALL}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + requirements)
    print(f"{Fore.GREEN}All packages installed!{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        import colorama
        import pyfiglet
        from ascii_magic import AsciiArt
    except ImportError:
        print(f"{Fore.YELLOW}Some required packages are missing. Installing...{Style.RESET_ALL}")
        install_requirements()
    connector = VoiceConnector()
    asyncio.run(connector.run())
