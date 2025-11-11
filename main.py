import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    ContextTypes, filters
)

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_GROUP_ID = os.getenv("TARGET_GROUP_ID")
ADMIN_IDS_ENV = os.getenv("ADMIN_IDS", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not TARGET_GROUP_ID:
    raise RuntimeError("TARGET_GROUP_ID not set")

TARGET_GROUP_ID = int(TARGET_GROUP_ID)

# parse admin ids
ADMIN_IDS = []
for part in ADMIN_IDS_ENV.split(","):
    part = part.strip()
    if part:
        try:
            ADMIN_IDS.append(int(part))
        except ValueError:
            pass  # ignore bad ones


def build_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("💬 ក្រុមចាត់", url="https://t.me/yourgroup"),
            InlineKeyboardButton("🎬 វីដេអូថ្មីៗ", url="https://t.me/yourchannel"),
        ],
        [
            InlineKeyboardButton("📱 បែបបទរាយការណ៍", url="https://yourwebsite.com/form"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 Bot ready!\n\n"
        "• Send me a video here (admin only) → I will post to target group\n"
        "• Or post video in channel (where I'm admin) → I will auto repost to group\n\n"
        "✅ 3 buttons will be attached automatically."
    )
    await update.message.reply_text(text)


async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post:
        return

    file_id = None
    if post.video:
        file_id = post.video.file_id
    elif post.document and post.document.mime_type and post.document.mime_type.startswith("video/"):
        file_id = post.document.file_id

    if not file_id:
        return

    caption = post.caption or ""
    await context.bot.send_video(
        chat_id=TARGET_GROUP_ID,
        video=file_id,
        caption=caption,
        reply_markup=build_keyboard()
    )


async def video_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user_id = msg.from_user.id
    if user_id not in ADMIN_IDS:
        await msg.reply_text("🚫 You are not allowed to post to group.")
        return

    file_id = None
    if msg.video:
        file_id = msg.video.file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"):
        file_id = msg.document.file_id

    if not file_id:
        return

    caption = msg.caption or ""
    await context.bot.send_video(
        chat_id=TARGET_GROUP_ID,
        video=file_id,
        caption=caption,
        reply_markup=build_keyboard()
    )
    await msg.reply_text("✅ Posted to group!")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.VIDEO | filters.Document.VIDEO),
        video_from_admin
    ))
    print("🤖 Bot running ...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
