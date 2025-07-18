# Voice Connector

Voice Connectotr Is A Python Script to keep your Discord account connected to a voice channel 24/7.

## Features

- Automatically connects to a voice channel of your choice
- Automatically reconnects.
- Simple setup and configuration via `.env` file
## Prerequisites

- Python 3.7 or higher
- Discord account with a user token

## Installation

1. Clone this repository or download the files
2. Run `install.bat` (Windows) or install the requirements manually:
   ```
   pip install -r requirements.txt
   ```
3. Edit the `.env` file with your Discord token and settings

## Configuration

Edit the `.env` file with the following settings:

```
# Required: Your Discord token (bot or user token)
TOKEN=your_token_here

# Optional: Your online status (online/dnd/idle)
DISCORD_STATUS=dnd

# Required: Server (Guild) ID where the voice channel is located
GUILD_ID=your_guild_id

# Required: Voice Channel ID to connect to
CHANNEL_ID=your_channel_id

# Optional: Self-mute in voice (True/False)
SELF_MUTE=True

# Optional: Self-deafen in voice (True/False)
SELF_DEAF=False
```

## Usage

1. Make sure you've configured the `.env` file
2. Run the script:
   ```
   python voice_connector.py
   ```
3. The script will automatically connect to the specified voice channel
4. To stop the script, press `Ctrl+C` in the terminal

## Running 24/7

To keep the script running 24/7, consider using:
- KataBump Or Wispbyte
## Notes

- User accounts using self-bots may be against Discord's Terms of Service
- Use at your own risk

## License

This project is for educational purposes only.
