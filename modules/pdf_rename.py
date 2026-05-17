import os
import time
import asyncio
from pyromod import listen
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import FloodWait

import globals
from vars import AUTH_USERS, OWNER
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

def register_pdf_rename_handlers(bot):

    @bot.on_message(filters.command("pdfrename") & filters.private)
    async def pdf_rename_cmd(client, m: Message):
        """
        /pdfrename — starts the PDF rename flow.
        Then bot asks to send the PDF document, then asks for new name.
        """
        if m.chat.id not in AUTH_USERS:
            await m.reply_text(
                f"<blockquote>__**Oopss! You are not a Premium member**__\n"
                f"__**Please Upgrade Your Plan**__\n"
                f"__**Your User id**__ - `{m.chat.id}`</blockquote>\n"
            )
            return

        editable = await m.reply_text(
            "**📄 PDF Rename Feature**\n\n"
            "Send the PDF file you want to rename.\n"
            "<blockquote>Or send /cancel to abort.</blockquote>"
        )
        try:
            pdf_msg: Message = await bot.listen(m.chat.id, timeout=120)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout! No PDF received. Please try again.")
            return

        if pdf_msg.text and pdf_msg.text.lower() == "/cancel":
            await editable.edit("❌ PDF Rename cancelled.")
            await pdf_msg.delete()
            return

        if not (pdf_msg.document and pdf_msg.document.file_name.lower().endswith(".pdf")):
            await editable.edit("❌ Please send a valid PDF file. Operation cancelled.")
            return

        original_name = pdf_msg.document.file_name
        await editable.edit(
            f"**📄 PDF received:** `{original_name}`\n\n"
            f"Now send the **new file name** (without .pdf extension).\n"
            f"<blockquote>Or send /cancel to abort.</blockquote>"
        )

        try:
            name_msg: Message = await bot.listen(m.chat.id, timeout=120)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout! No name received. Please try again.")
            return

        if name_msg.text and name_msg.text.lower() == "/cancel":
            await editable.edit("❌ PDF Rename cancelled.")
            await name_msg.delete()
            return

        new_name = name_msg.text.strip()
        # Sanitize filename - remove invalid characters
        new_name = "".join(c for c in new_name if c not in r'\/:*?"<>|')
        if not new_name:
            await editable.edit("❌ Invalid file name. Please try again with /pdfrename.")
            await name_msg.delete()
            return

        new_filename = f"{new_name}.pdf"
        await name_msg.delete()
        await editable.edit(f"⏳ **Downloading PDF...** Please wait.")

        try:
            download_path = await bot.download_media(pdf_msg, file_name=f"downloads/{original_name}")
        except Exception as e:
            await editable.edit(f"❌ **Download failed:**\n<blockquote>{str(e)}</blockquote>")
            return

        # Rename the file
        dir_path = os.path.dirname(download_path)
        renamed_path = os.path.join(dir_path, new_filename)
        try:
            os.rename(download_path, renamed_path)
        except Exception as e:
            await editable.edit(f"❌ **Rename failed:**\n<blockquote>{str(e)}</blockquote>")
            if os.path.exists(download_path):
                os.remove(download_path)
            return

        await editable.edit(f"📤 **Uploading renamed PDF:** `{new_filename}`...")

        # Apply pdfthumb if set
        pdfthumb = globals.pdfthumb
        thumbnail = None
        if pdfthumb and pdfthumb != "/d":
            thumbnail = pdfthumb

        try:
            try:
                await bot.send_document(
                    m.chat.id,
                    document=renamed_path,
                    file_name=new_filename,
                    caption=f"**📄 {new_filename}**",
                    thumb=thumbnail
                )
            except Exception:
                await bot.send_document(
                    m.chat.id,
                    document=renamed_path,
                    file_name=new_filename,
                    caption=f"**📄 {new_filename}**"
                )
            await editable.edit(f"✅ **PDF renamed and uploaded successfully!**\n`{original_name}` → `{new_filename}`")
        except Exception as e:
            await editable.edit(f"❌ **Upload failed:**\n<blockquote>{str(e)}</blockquote>")
        finally:
            if os.path.exists(renamed_path):
                os.remove(renamed_path)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
