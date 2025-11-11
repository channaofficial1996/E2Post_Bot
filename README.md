# Telegram Auto Video Poster Bot (Railway Ready)

This project is ready for Railway.

## Files
- main.py
- requirements.txt
- Procfile
- runtime.txt  ← force Python 3.11.8 on Railway
- README.md

## Env Vars to set on Railway

- BOT_TOKEN = your telegram bot token
- TARGET_GROUP_ID = -100xxxxxxxxxx
- ADMIN_IDS = 123456789,987654321

## What it does
- If bot is admin in a channel: every video posted there is auto-posted to target group with 3 buttons.
- If an admin sends a video to the bot in private: the bot posts it to the target group with the same 3 buttons.
