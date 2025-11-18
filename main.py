import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatMemberStatus

# ====== ENV CONFIG ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
# អាចដាក់ជា TARGET_GROUP_IDS=-1001,-1002,-1003
TARGET_GROUP_IDS_ENV = os.getenv("TARGET_GROUP_IDS") or os.getenv("TARGET_GROUP_ID", "")
ADMIN_IDS_ENV = os.getenv("ADMIN_IDS", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not TARGET_GROUP_IDS_ENV:
    raise RuntimeError("TARGET_GROUP_IDS not set")

# parse group ids → list[int]
TARGET_GROUP_IDS = []
for part in TARGET_GROUP_IDS_ENV.split(","):
    part = part.strip()
    if part:
        try:
            TARGET_GROUP_IDS.append(int(part))
        except ValueError:
            pass

# parse admin ids → list[int]
ADMIN_IDS = []
for part in ADMIN_IDS_ENV.split(","):
    part = part.strip()
    if part:
        try:
            ADMIN_IDS.append(int(part))
        except ValueError:
            pass

# ====== STATE KEYS ======
STATE_KEY = "state"
MEDIA_KEY = "media"

STATE_WAIT_MEDIA = "wait_media"
STATE_WAIT_CAPTION = "wait_caption"


def build_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🐓ជជែកគ្នា⚽️", url="https://t.me/E2public"),
                InlineKeyboardButton("🎬រូបភាព&វីដេអូ", url="https://t.me/+L7kr82tH6ts5MjVl"),
            ],
            [
                InlineKeyboardButton("☎️បើកអាខោន", url="https://t.me/E2betcs"),
            ],
        ]
    )


def build_reply_keyboard() -> ReplyKeyboardMarkup:
    # keyboard ដែលនៅជាប់ខាងក្រោម
    kb = [[KeyboardButton("▶️ ចាប់ផ្តើម")]]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)


# ====== AUTO DELETE HELPERS ======
async def is_user_chat_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    """Check if user is Telegram admin/owner in this chat."""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


def is_sender_bot_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    msg = update.effective_message
    if not msg or not msg.from_user:
        return False
    return msg.from_user.is_bot and (msg.from_user.id == context.bot.id)


def is_sender_anonymous_admin_or_linked_channel(update: Update) -> bool:
    """
    If admin post as 'anonymous admin' or as linked channel,
    Telegram will set sender_chat instead of from_user.
    Those messages should NOT be deleted.
    """
    msg = update.effective_message
    if not msg:
        return False
    return msg.sender_chat is not None


# ====== HANDLERS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    await update.message.reply_text(
        "📥 សូមផ្ញើ វីដេអូ ឬ រូបភាព មក bot នេះសិន\n"
        "បន្ទាប់មកបញ្ចូល caption📤",
        reply_markup=build_reply_keyboard(),
    )


async def start_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ពេលចុច ▶️ ចាប់ផ្តើម
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    await update.message.reply_text("🎬 សូមផ្ញើ វីដេអូ ឬ រូបភាព មក bot នេះសិន")


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    # check admin
    if user_id not in ADMIN_IDS:
        await msg.reply_text("🚫 អ្នកមិនមានសិទ្ធិបោះទៅក្រុមទេ!")
        return

    media_info = {}

    if msg.video:
        media_info["type"] = "video"
        media_info["file_id"] = msg.video.file_id
    elif msg.photo:
        media_info["type"] = "photo"
        media_info["file_id"] = msg.photo[-1].file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"):
        media_info["type"] = "video"
        media_info["file_id"] = msg.document.file_id
    else:
        await msg.reply_text("⚠️ សូមផ្ញើតែ វីដេអូ ឬ រូបភាព ប៉ុណ្ណោះ.")
        return

    # keep media for next step
    context.user_data[MEDIA_KEY] = media_info
    context.user_data[STATE_KEY] = STATE_WAIT_CAPTION

    await msg.reply_text(
        "📝 សូមបញ្ចូល caption ឥឡូវនេះ\n"
        "➡ អាចដាក់អក្សរយូរបាន និងដាក់ Link បានគ្រប់យ៉ាង។"
    )


async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    # need to be in caption state
    if context.user_data.get(STATE_KEY) != STATE_WAIT_CAPTION:
        # maybe user just typed random text
        return

    if user_id not in ADMIN_IDS:
        await msg.reply_text("🚫 អ្នកមិនមានសិទ្ធិ!")
        return

    caption_text = msg.text or ""
    media_info = context.user_data.get(MEDIA_KEY)
    if not media_info:
        await msg.reply_text("❗ មិនមានវីដេអូ/រូបភាពដែលបានផ្ញើមុនទេ។ សូម /start សារជាថ្មី.")
        context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
        return

    success = 0
    errors = []

    for gid in TARGET_GROUP_IDS:
        try:
            if media_info["type"] == "video":
                await context.bot.send_video(
                    chat_id=gid,
                    video=media_info["file_id"],
                    caption=caption_text,
                    reply_markup=build_inline_keyboard(),
                )
            else:
                await context.bot.send_photo(
                    chat_id=gid,
                    photo=media_info["file_id"],
                    caption=caption_text,
                    reply_markup=build_inline_keyboard(),
                )
            success += 1
        except Exception as e:
            errors.append(f"{gid}: {e}")

    if success and not errors:
        await msg.reply_text(f"✅ បានបញ្ជូនទៅ Group ចំនួន {success} ជោគជ័យ!", reply_markup=build_reply_keyboard())
    elif success and errors:
        await msg.reply_text(
            "⚠️ បញ្ជូនបានខ្លះ ប៉ុន្តែខ្លះបរាជ័យ:\n" + "\n".join(errors),
            reply_markup=build_reply_keyboard(),
        )
    else:
        await msg.reply_text("❌ បញ្ជូនមិនបានទៅក្រុមណាម្ម៉ងទេ.", reply_markup=build_reply_keyboard())

    # reset state
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    context.user_data.pop(MEDIA_KEY, None)


async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # auto repost from channel → all groups
    post = update.channel_post
    if not post:
        return

    file_id = None
    media_type = None

    if post.video:
        file_id = post.video.file_id
        media_type = "video"
    elif post.photo:
        file_id = post.photo[-1].file_id
        media_type = "photo"
    elif post.document and post.document.mime_type and post.document.mime_type.startswith("video/"):
        file_id = post.document.file_id
        media_type = "video"

    if not file_id:
        return

    caption = post.caption or ""

    for gid in TARGET_GROUP_IDS:
        try:
            if media_type == "video":
                await context.bot.send_video(
                    chat_id=gid,
                    video=file_id,
                    caption=caption,
                    reply_markup=build_inline_keyboard(),
                )
            else:
                await context.bot.send_photo(
                    chat_id=gid,
                    photo=file_id,
                    caption=caption,
                    reply_markup=build_inline_keyboard(),
                )
        except Exception as e:
            print(f"error send to {gid}: {e}")


# ====== GROUP AUTO DELETE (NEW) ======
async def group_auto_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Auto delete post in target groups if sender is NOT:
    - user in ADMIN_IDS (bot admin), OR
    - Telegram chat admin/owner, OR
    - this bot itself, OR
    - anonymous admin / linked channel (sender_chat).
    """
    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not chat:
        return

    # Only moderate in configured target groups
    if chat.id not in TARGET_GROUP_IDS:
        return

    # Skip service messages (join, leave, pin, etc.)
    if msg.new_chat_members or msg.left_chat_member or msg.pinned_message or msg.group_chat_created:
        return

    # Skip messages sent by this bot
    if is_sender_bot_self(update, context):
        return

    # Skip anonymous admins / linked channels
    if is_sender_anonymous_admin_or_linked_channel(update):
        return

    # If no from_user, cannot decide safely
    if not msg.from_user:
        return

    user_id = msg.from_user.id

    # Whitelist bot admin IDs from env
    if user_id in ADMIN_IDS:
        return

    # Allow real chat admins/owner
    if await is_user_chat_admin(context, chat.id, user_id):
        return

    # If none of the above -> delete this message
    try:
        await context.bot.delete_message(chat_id=chat.id, message_id=msg.message_id)
    except Exception as e:
        # មិនបាច់ raise ដោយកុំឲ្យ bot ឈប់
        # print(f"delete failed in {chat.id}: {e}")
        pass


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # /start
    app.add_handler(CommandHandler("start", start))

    # pinned "▶️ ចាប់ផ្តើម"
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & filters.Regex("^▶️ ចាប់ផ្តើម"),
            start_button,
        )
    )

    # channel auto-post
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))

    # media step (private)
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (filters.VIDEO | filters.PHOTO | filters.Document.VIDEO),
            handle_media,
        )
    )

    # caption step (private text, not command)
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND),
            handle_caption,
        )
    )

    # ====== GROUP AUTO DELETE HANDLER (NEW) ======
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL,
            group_auto_delete,
        )
    )

    print("🤖 Bot running ...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
