import os
import asyncio
import time
from pyromod import listen
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import FloodWait

import globals
from vars import AUTH_USERS, OWNER, CREDIT
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

def register_pdf_rename_handlers(bot):

    @bot.on_message(filters.command("pdfrename") & filters.private)
    async def pdf_rename_cmd(client, m: Message):
        """
        /pdfrename — PDF rename flow:
        1. Bot asks to send PDF
        2. Bot asks for new name
        3. Bot asks for batch name (like /unknown system)
        4. Bot applies pdfthumb (if set) and uploads with cc1 style caption
        """
        if m.chat.id not in AUTH_USERS:
            await m.reply_text(
                f"<blockquote>__**Oopss! You are not a Premium member**__\n"
                f"__**Please Upgrade Your Plan**__\n"
                f"__**Your User id**__ - `{m.chat.id}`</blockquote>\n"
            )
            return

        editable = await m.reply_text(
            "**📄 PDF Rename**\n\n"
            "**Step 1/3:** Send the PDF file you want to rename.\n"
            "<blockquote>Send /cancel to abort.</blockquote>"
        )

        # Step 1: Wait for PDF file
        try:
            pdf_msg: Message = await bot.listen(m.chat.id, timeout=120)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout! No PDF received. Please try /pdfrename again.")
            return

        if pdf_msg.text and pdf_msg.text.strip().lower() == "/cancel":
            await editable.edit("❌ PDF Rename cancelled.")
            await pdf_msg.delete()
            return

        # Accept PDF with or without caption
        if not (pdf_msg.document and pdf_msg.document.file_name.lower().endswith(".pdf")):
            await editable.edit("❌ Please send a valid PDF document. Operation cancelled.")
            return

        original_name = pdf_msg.document.file_name

        # Step 2: Ask for new name
        await editable.edit(
            f"**📄 PDF received:** `{original_name}`\n\n"
            f"**Step 2/3:** Send the **new file name** (without .pdf extension).\n"
            f"<blockquote>Send /cancel to abort.</blockquote>"
        )
        try:
            name_msg: Message = await bot.listen(m.chat.id, timeout=120)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout! No name received. Please try /pdfrename again.")
            return

        if name_msg.text and name_msg.text.strip().lower() == "/cancel":
            await editable.edit("❌ PDF Rename cancelled.")
            await name_msg.delete()
            return

        new_name_raw = name_msg.text.strip()
        await name_msg.delete()

        # Sanitize filename
        new_name = "".join(c for c in new_name_raw if c not in r'\/:*?"<>|')
        if not new_name:
            await editable.edit("❌ Invalid file name. Please try /pdfrename again.")
            return

        # Apply endfilename suffix if set in settings
        endfilename = globals.endfilename
        if endfilename and endfilename != "/d":
            new_name_final = f"{new_name} {endfilename}"
        else:
            new_name_final = new_name

        new_filename = f"{new_name_final}.pdf"

        # Step 3: Ask for batch name
        await editable.edit(
            f"**Step 3/3:** Enter **Batch Name** or send **/unknown** if you don't know.\n"
            f"<blockquote>This will appear in the caption below the file.</blockquote>"
        )
        try:
            batch_msg: Message = await bot.listen(m.chat.id, timeout=120)
        except asyncio.TimeoutError:
            b_name = "Unknow Batch😕😂."
            batch_msg = None
        else:
            b_text = batch_msg.text.strip() if batch_msg.text else "/unknown"
            b_name = "Unknow Batch😕😂." if b_text.lower() in ["/unknown", "/unknow"] else b_text
            await batch_msg.delete()

        await editable.edit(f"⏳ Downloading PDF... Please wait.")

        # Download the PDF
        os.makedirs("downloads", exist_ok=True)
        try:
            download_path = await bot.download_media(
                pdf_msg,
                file_name=f"downloads/{original_name}"
            )
        except Exception as e:
            await editable.edit(f"❌ **Download failed:**\n<blockquote>{str(e)}</blockquote>")
            return

        # Rename the file locally
        dir_path = os.path.dirname(download_path)
        renamed_path = os.path.join(dir_path, new_filename)
        try:
            os.rename(download_path, renamed_path)
        except Exception as e:
            await editable.edit(f"❌ **Rename failed:**\n<blockquote>{str(e)}</blockquote>")
            if os.path.exists(download_path):
                os.remove(download_path)
            return

        await editable.edit(f"📤 Uploading renamed PDF: `{new_filename}`...")

        # Build caption — cc1 style (same as drm_handler PDF cc1)
        CR = globals.CR
        count_str = "001"
        cc1 = (
            f"**💾 PDF_ID: {count_str}.\n\n"
            f"📝 Title: {new_name_final} .pdf\n\n"
            f"<pre><code>📚 Batch Name: {b_name}</code></pre>\n\n"
            f"📥 Extracted By♠ : {CR}\n\n"
            f"**➽━━━⊱∘₊𝙏𝙚𝙖𝙢★𝙏𝙤𝙭𝙞𝙘₊∘⊰━━━❥**"
        )

        # Resolve PDF thumbnail
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
                    caption=cc1,
                    thumb=thumbnail
                )
            except Exception:
                await bot.send_document(
                    m.chat.id,
                    document=renamed_path,
                    file_name=new_filename,
                    caption=cc1
                )
            await editable.edit(
                f"✅ **PDF renamed and uploaded!**\n"
                f"`{original_name}` → `{new_filename}`"
            )
        except Exception as e:
            await editable.edit(f"❌ **Upload failed:**\n<blockquote>{str(e)}</blockquote>")
        finally:
            if os.path.exists(renamed_path):
                os.remove(renamed_path)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
