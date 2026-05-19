"""
video_cover.py — Video Cover (Thumbnail) System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• /setvideocover  — Global video cover set karo (direct Telegram photo only, URL not supported)
• /viewvideocover — Current video cover dekho
• /delvideocover  — Video cover delete karo

• /MS send karne par global settings wala cover use hoga
• Agar global cover set nahi hai to user se image maango
• Bot restart ke baad bhi saved rehta hai (JSON file mein)
• Sirf AUTH_USERS use kar sakte hain
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import json
import uuid
import asyncio

import globals
from vars import AUTH_USERS, CREDIT
from pyrogram import Client, filters
from pyrogram.types import Message

# ── Persistent store file ────────────────────────────────────────────────────
_VCOVER_STORE = "videocover_store.json"

# ────────────────────────────────────────────────────────────────────────────
# Storage helpers
# ────────────────────────────────────────────────────────────────────────────

def _load_vcover_store() -> dict:
    if os.path.exists(_VCOVER_STORE):
        try:
            with open(_VCOVER_STORE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_vcover_store(data: dict):
    try:
        with open(_VCOVER_STORE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[video_cover] Save error: {e}")


def save_videocover_for_user(user_id: int, cover_value: str):
    data = _load_vcover_store()
    data[str(user_id)] = cover_value
    _save_vcover_store(data)
    # Also update global
    globals.videocover = cover_value


def get_videocover_for_user(user_id: int) -> str:
    data = _load_vcover_store()
    return data.get(str(user_id), "/d")


def delete_videocover_for_user(user_id: int):
    data = _load_vcover_store()
    data.pop(str(user_id), None)
    _save_vcover_store(data)
    globals.videocover = "/d"


def load_global_videocover_on_start():
    """Bot start par globals.videocover load karo from store."""
    data = _load_vcover_store()
    if data:
        last_val = list(data.values())[-1]
        if last_val and last_val != "/d":
            globals.videocover = last_val
            print(f"[video_cover] Loaded videocover from store: {last_val[:60]}")


# ────────────────────────────────────────────────────────────────────────────
# Handler registration
# ────────────────────────────────────────────────────────────────────────────

def register_video_cover_handlers(bot: Client):

    # ── /setvideocover ────────────────────────────────────────────────────────
    @bot.on_message(filters.command(["setvideocover", "videocover"]) & filters.private)
    async def set_videocover_cmd(client: Client, m: Message):
        if m.chat.id not in AUTH_USERS:
            await m.reply_text(
                f"<blockquote>__**Oopss! You are not a Premium member**__\n"
                f"__**Your User id**__ - `{m.chat.id}`</blockquote>"
            )
            return

        editable = await m.reply_text(
            "**🎥 Video Cover Set — Step 1/1**\n\n"
            "📸 **Direct Telegram se photo bhejo** as Video Cover.\n\n"
            "<blockquote>⚠️ Note: Sirf Telegram photo supported hai.\n"
            "URL supported nahi hai.\n\n"
            "Send /d to disable cover.\n"
            "Send /cancel to abort.</blockquote>"
        )

        try:
            inp: Message = await bot.listen(m.chat.id, timeout=120)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout! Please try /setvideocover again.")
            return

        # Cancel check
        if inp.text and inp.text.strip().lower() == "/cancel":
            await editable.edit("❌ Cancelled.")
            await inp.delete(True)
            return

        # Disable
        if inp.text and inp.text.strip().lower() == "/d":
            globals.videocover = "/d"
            delete_videocover_for_user(m.chat.id)
            await editable.edit(
                "✅ **Video Cover disabled!**\n"
                "Ab videos bina custom cover ke upload honge."
            )
            await inp.delete(True)
            return

        # Photo sent
        if inp.photo:
            file_id = inp.photo.file_id
            globals.videocover = file_id
            save_videocover_for_user(m.chat.id, file_id)
            await editable.edit(
                "✅ **Video Cover set successfully!**\n"
                "<blockquote>Ye cover ab /setvideocover command aur video rename mein use hoga.\n"
                "Bot restart ke baad bhi saved rahega.</blockquote>"
            )
            await inp.delete(True)
            return

        # Invalid
        await editable.edit(
            "❌ Invalid input!\n"
            "Sirf Telegram photo bhejein (URL supported nahi).\n"
            "Try /setvideocover again."
        )
        await inp.delete(True)

    # ── /viewvideocover ───────────────────────────────────────────────────────
    @bot.on_message(filters.command(["viewvideocover", "vvideocover"]) & filters.private)
    async def view_videocover_cmd(client: Client, m: Message):
        if m.chat.id not in AUTH_USERS:
            await m.reply_text(
                f"<blockquote>__**Oopss! You are not a Premium member**__\n"
                f"__**Your User id**__ - `{m.chat.id}`</blockquote>"
            )
            return

        saved = get_videocover_for_user(m.chat.id)
        if saved == "/d" or not saved:
            await m.reply_text(
                "📭 **Video Cover set nahi hai.**\n\n"
                "Use /setvideocover to set one."
            )
            return

        try:
            await m.reply_photo(
                photo=saved,
                caption=(
                    "🎥 **Your Video Cover**\n\n"
                    "<blockquote>Type: Direct Photo (Telegram)\n"
                    "Status: ✅ Active</blockquote>"
                )
            )
        except Exception as e:
            await m.reply_text(
                f"🎥 Video Cover set hai.\n\n"
                f"⚠️ Preview load nahi hua: {str(e)[:100]}"
            )

    # ── /delvideocover ────────────────────────────────────────────────────────
    @bot.on_message(filters.command(["delvideocover", "removevideocover"]) & filters.private)
    async def del_videocover_cmd(client: Client, m: Message):
        if m.chat.id not in AUTH_USERS:
            await m.reply_text(
                f"<blockquote>__**Oopss! You are not a Premium member**__\n"
                f"__**Your User id**__ - `{m.chat.id}`</blockquote>"
            )
            return

        saved = get_videocover_for_user(m.chat.id)
        if saved == "/d" or not saved:
            await m.reply_text("📭 **Koi video cover set nahi hai already.**")
            return

        globals.videocover = "/d"
        delete_videocover_for_user(m.chat.id)
        await m.reply_text(
            "❌ **Video Cover deleted!**\n\n"
            "Ab videos bina custom cover ke upload honge.\n"
            "Use /setvideocover to set a new one."
        )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
