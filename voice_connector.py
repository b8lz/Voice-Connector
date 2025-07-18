import os
import sys
import json
import time
import asyncio
import websockets
import random
import platform
from datetime import datetime
from dotenv import load_dotenv
from colorama import init, Fore, Style
from pyfiglet import Figlet
from ascii_magic import AsciiArt

init(autoreset=True)

def show_error_message(message):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Token Missing", message)
        root.destroy()
    except:
        print(f"{Fore.RED}[ERROR] {message}{Style.RESET_ALL}")
    
    os.system(f'notepad "{os.path.abspath(".env")}"')
    sys.exit(1)

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
        self.username = "User"
        self.discriminator = "0000"
        self.user_id = "0"
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10

    async def display_banner(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.CYAN}{'='*50}")
        print(f"Voice Connector - Stay In VC 24/7")
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
                if self.websocket and self.websocket.open:
                    await self.websocket.send(json.dumps({"op": 1, "d": self.sequence}))
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
        'websockets>=10.0',
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
