import os
import uuid
import asyncio
import requests
from pyromod import listen
from pyrogram import Client, filters
from pyrogram.types import Message

import globals
from vars import AUTH_USERS, CREDIT
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

def register_pdf_rename_handlers(bot):

    @bot.on_message(filters.command("pdfrename") & filters.private)
    async def pdf_rename_cmd(client, m: Message):
        """
        /pdfrename — 3-step PDF rename:
        1. Bot asks for PDF file
        2. Bot asks for new name
        3. Bot asks for batch name (like /unknown system in drm_handler)
        Then re-uploads with cc1 caption style + pdfthumb if set
        """
        if m.chat.id not in AUTH_USERS:
            await m.reply_text(
                f"<blockquote>__**Oopss! You are not a Premium member**__\n"
                f"__**Please Upgrade Your Plan**__\n"
                f"__**Your User id**__ - `{m.chat.id}`</blockquote>\n"
            )
            return

        # Step 1: Ask for PDF file
        editable = await m.reply_text(
            "**📄 PDF Rename — Step 1/3**\n\n"
            "Send the PDF file you want to rename.\n"
            "<blockquote>Send /cancel to abort.</blockquote>"
        )

        try:
            pdf_msg: Message = await bot.listen(m.chat.id, timeout=120)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout! Please try /pdfrename again.")
            return

        if pdf_msg.text and pdf_msg.text.strip().lower() == "/cancel":
            await editable.edit("❌ Cancelled.")
            await pdf_msg.delete()
            return

        # Accept any document ending in .pdf (with or without caption)
        if not (pdf_msg.document and pdf_msg.document.file_name.lower().endswith(".pdf")):
            await editable.edit("❌ Please send a valid PDF file. Use /pdfrename again.")
            return

        original_name = pdf_msg.document.file_name

        # Step 2: Ask for new name
        await editable.edit(
            f"**📄 Step 2/3**\n\n"
            f"PDF received: `{original_name}`\n\n"
            f"Send the **new file name** (without .pdf).\n"
            f"<blockquote>Send /cancel to abort.</blockquote>"
        )
        try:
            name_msg: Message = await bot.listen(m.chat.id, timeout=120)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout! Please try /pdfrename again.")
            return

        if name_msg.text and name_msg.text.strip().lower() == "/cancel":
            await editable.edit("❌ Cancelled.")
            await name_msg.delete()
            return

        new_name_raw = name_msg.text.strip() if name_msg.text else ""
        await name_msg.delete()

        # Sanitize
        new_name = "".join(c for c in new_name_raw if c not in r'\/:*?"<>|')
        if not new_name:
            await editable.edit("❌ Invalid file name. Use /pdfrename again.")
            return

        # Apply endfilename suffix from settings if set
        endfilename = globals.endfilename
        if endfilename and endfilename != "/d":
            new_name_final = f"{new_name} {endfilename}"
        else:
            new_name_final = new_name

        new_filename = f"{new_name_final}.pdf"

        # Step 3: Ask for batch name
        await editable.edit(
            f"**📄 Step 3/3**\n\n"
            f"Enter **Batch Name** or send **/unknown** if you don't know.\n"
            f"<blockquote>Same /unknown system as direct link download.</blockquote>"
        )
        try:
            batch_msg: Message = await bot.listen(m.chat.id, timeout=120)
            b_text = batch_msg.text.strip() if batch_msg.text else "/unknown"
            b_name = "Unknow Batch😕😂." if b_text.lower() in ["/unknown", "/unknow"] else b_text
            await batch_msg.delete()
        except asyncio.TimeoutError:
            b_name = "Unknow Batch😕😂."

        await editable.edit("⏳ Downloading PDF... Please wait.")

        # Download PDF
        os.makedirs("downloads", exist_ok=True)
        safe_dl_name = f"pdfrn_{uuid.uuid4().hex}.pdf"
        try:
            download_path = await bot.download_media(
                pdf_msg,
                file_name=f"downloads/{safe_dl_name}"
            )
        except Exception as e:
            await editable.edit(f"❌ Download failed:\n<blockquote>{str(e)[:300]}</blockquote>")
            return

        # Rename locally
        dir_path = os.path.dirname(download_path)
        renamed_path = os.path.join(dir_path, new_filename)
        try:
            os.rename(download_path, renamed_path)
        except Exception as e:
            await editable.edit(f"❌ Rename failed:\n<blockquote>{str(e)[:300]}</blockquote>")
            if os.path.exists(download_path):
                os.remove(download_path)
            return

        await editable.edit(f"📤 Uploading: `{new_filename}`...")

        # Build cc1-style caption
        CR = globals.CR
        cc1 = (
            f"**💾 PDF_ID: 001.\n\n"
            f"📝 Title: {new_name_final} .pdf\n\n"
            f"<pre><code>📚 Batch Name: {b_name}</code></pre>\n\n"
            f"📥 Extracted By♠ : {CR}\n\n"
            f"**➽━━━⊱∘₊𝙏𝙚𝙖𝙢★𝙏𝙤𝙭𝙞𝙘₊∘⊰━━━❥**"
        )

        # Resolve pdfthumb — must be local file for Pyrogram
        pdfthumb = globals.pdfthumb
        thumbnail = None
        local_thumb = None
        if pdfthumb and pdfthumb != "/d":
            if pdfthumb.startswith("http://") or pdfthumb.startswith("https://"):
                local_thumb = f"pdfthumb_{uuid.uuid4().hex}.jpg"
                try:
                    dl = requests.get(pdfthumb, timeout=15)
                    if dl.status_code == 200:
                        with open(local_thumb, "wb") as tf:
                            tf.write(dl.content)
                        thumbnail = local_thumb
                except Exception as e:
                    print(f"PDF thumb download failed: {e}")
            elif os.path.exists(pdfthumb):
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
                f"✅ **Done!**\n"
                f"`{original_name}` → `{new_filename}`"
            )
        except Exception as e:
            await editable.edit(f"❌ Upload failed:\n<blockquote>{str(e)[:300]}</blockquote>")
        finally:
            if os.path.exists(renamed_path):
                os.remove(renamed_path)
            if local_thumb and os.path.exists(local_thumb):
                os.remove(local_thumb)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
