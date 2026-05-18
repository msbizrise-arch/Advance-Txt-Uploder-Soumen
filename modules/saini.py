import os
import re
import time
import mmap
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import tgcrypto
import subprocess
import concurrent.futures
from math import ceil
from utils import progress_bar
from pyrogram import Client, filters
from pyrogram.types import Message
from io import BytesIO
from pathlib import Path  
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode

def duration(filename):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1", filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        output = result.stdout.decode("utf-8", errors="ignore").strip()
        if not output:
            # fallback: try stderr too
            output = result.stderr.decode("utf-8", errors="ignore").strip()
        return float(output) if output else 0.0
    except Exception:
        return 0.0
 
def exec(cmd):
        process = subprocess.run(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        output = process.stdout.decode()
        print(output)
        return output
        #err = process.stdout.decode()

def pull_run(work, cmds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:
        print("Waiting for tasks to complete")
        fut = executor.map(exec,cmds)
        
async def aio(url,name):
    k = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(k, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return k


async def download(url,name):
    ka = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(ka, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return ka


def parse_vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = []
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ",2)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))
            except:
                pass
    return new_info

def vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = dict()
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ",3)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    
                    # temp.update(f'{i[2]}')
                    # new_info.append((i[2], i[0]))
                    #  mp4,mkv etc ==== f"({i[1]})" 
                    
                    new_info.update({f'{i[2]}':f'{i[0]}'})

            except:
                pass
    return new_info


async def decrypt_and_merge_video(mpd_url, keys_string, output_path, output_name, quality="720"):
    try:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        cmd1 = f'yt-dlp -f "bv[height<={quality}]+ba/b" -o "{output_path}/file.%(ext)s" --allow-unplayable-format --no-check-certificate --external-downloader aria2c "{mpd_url}"'
        print(f"Running command: {cmd1}")
        os.system(cmd1)
        
        avDir = list(output_path.iterdir())
        print(f"Downloaded files: {avDir}")
        print("Decrypting")

        video_decrypted = False
        audio_decrypted = False

        for data in avDir:
            if data.suffix == ".mp4" and not video_decrypted:
                cmd2 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/video.mp4"'
                print(f"Running command: {cmd2}")
                os.system(cmd2)
                if (output_path / "video.mp4").exists():
                    video_decrypted = True
                data.unlink()
            elif data.suffix == ".m4a" and not audio_decrypted:
                cmd3 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/audio.m4a"'
                print(f"Running command: {cmd3}")
                os.system(cmd3)
                if (output_path / "audio.m4a").exists():
                    audio_decrypted = True
                data.unlink()

        if not video_decrypted or not audio_decrypted:
            raise FileNotFoundError("Decryption failed: video or audio file not found.")

        cmd4 = f'ffmpeg -i "{output_path}/video.mp4" -i "{output_path}/audio.m4a" -c copy "{output_path}/{output_name}.mp4"'
        print(f"Running command: {cmd4}")
        os.system(cmd4)
        if (output_path / "video.mp4").exists():
            (output_path / "video.mp4").unlink()
        if (output_path / "audio.m4a").exists():
            (output_path / "audio.m4a").unlink()
        
        filename = output_path / f"{output_name}.mp4"

        if not filename.exists():
            raise FileNotFoundError("Merged video file not found.")

        cmd5 = f'ffmpeg -i "{filename}" 2>&1 | grep "Duration"'
        duration_info = os.popen(cmd5).read()
        print(f"Duration info: {duration_info}")

        return str(filename)

    except Exception as e:
        print(f"Error during decryption and merging: {str(e)}")
        raise

async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if proc.returncode == 1:
        return False
    if stdout:
        return f'[stdout]\n{stdout.decode()}'
    if stderr:
        return f'[stderr]\n{stderr.decode()}'

    

def old_download(url, file_name, chunk_size = 1024 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
    return file_name


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"


async def download_video(url,cmd, name):
    download_cmd = f'{cmd} -R 25 --fragment-retries 25 --external-downloader aria2c --downloader-args "aria2c: -x 16 -j 32"'
    global failed_counter
    print(download_cmd)
    logging.info(download_cmd)
    try:
        k = subprocess.run(download_cmd, shell=True, timeout=3600)  # 1 hour max
    except subprocess.TimeoutExpired:
        print(f"Download timed out for: {name}")
        return name
    if "visionias" in cmd and k.returncode != 0 and failed_counter <= 10:
        failed_counter += 1
        await asyncio.sleep(5)
        await download_video(url, cmd, name)
    failed_counter = 0
    try:
        if os.path.isfile(name):
            return name
        elif os.path.isfile(f"{name}.webm"):
            return f"{name}.webm"
        name = name.split(".")[0]
        if os.path.isfile(f"{name}.mkv"):
            return f"{name}.mkv"
        elif os.path.isfile(f"{name}.mp4"):
            return f"{name}.mp4"
        elif os.path.isfile(f"{name}.mp4.webm"):
            return f"{name}.mp4.webm"

        return name
    except FileNotFoundError as exc:
        return os.path.isfile.splitext[0] + "." + "mp4"


async def apply_pdf_watermark(input_pdf, output_pdf, watermark_text):
    """Apply a diagonal text watermark to every page of a PDF — top-right, 45°, 30% opacity."""
    try:
        import io
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import Color

        # Try pypdf first (newer), fall back to PyPDF2
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            from PyPDF2 import PdfReader, PdfWriter

        reader = PdfReader(input_pdf)
        writer = PdfWriter()

        for page in reader.pages:
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            # Build watermark layer
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(page_width, page_height))
            c.saveState()

            font_size = max(10, int(page_width / 22))
            # 30% opacity black text (visible on white background PDFs)
            c.setFillColor(Color(0, 0, 0, alpha=0.3))
            c.setFont("Helvetica-Bold", font_size)

            # Top-right area, 45 degree rotation
            c.translate(page_width * 0.80, page_height * 0.85)
            c.rotate(45)
            c.drawCentredString(0, 0, watermark_text)
            c.restoreState()
            c.save()

            packet.seek(0)

            try:
                from pypdf import PdfReader as PR2
            except ImportError:
                from PyPDF2 import PdfReader as PR2

            wm_reader = PR2(packet)
            wm_page = wm_reader.pages[0]
            page.merge_page(wm_page)
            writer.add_page(page)

        with open(output_pdf, "wb") as f_out:
            writer.write(f_out)
        return True
    except Exception as e:
        print(f"PDF watermark error: {e}")
        return False


async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name, channel_id, pdfwatermark="/d", pdfthumb="/d"):
    import uuid
    reply = await bot.send_message(channel_id, f"Downloading pdf:\n<pre><code>{name}</code></pre>")
    time.sleep(1)

    final_pdf = ka
    watermarked = False
    local_thumb = None

    # Apply PDF watermark if set
    if pdfwatermark and pdfwatermark != "/d":
        wm_output = f"wm_{uuid.uuid4().hex}.pdf"
        try:
            success = await asyncio.wait_for(
                apply_pdf_watermark(ka, wm_output, pdfwatermark),
                timeout=120
            )
        except asyncio.TimeoutError:
            success = False
            print("PDF watermark timed out")
        if success and os.path.exists(wm_output):
            final_pdf = wm_output
            watermarked = True

    # Resolve thumbnail — Pyrogram needs LOCAL file, not URL
    thumbnail = None
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
                thumbnail = None
        elif os.path.exists(pdfthumb):
            thumbnail = pdfthumb

    reply_up = await bot.send_message(channel_id, f"**📩 Uploading PDF 📩:-**\n<blockquote>**{name}**</blockquote>")
    try:
        if thumbnail:
            await bot.send_document(channel_id, final_pdf, caption=cc1, thumb=thumbnail)
        else:
            await bot.send_document(channel_id, final_pdf, caption=cc1)
    except Exception as e:
        print(f"send_document error: {e}")
        try:
            await bot.send_document(channel_id, final_pdf, caption=cc1)
        except Exception as e2:
            print(f"send_document fallback error: {e2}")

    count += 1
    await reply.delete(True)
    await reply_up.delete(True)
    time.sleep(1)
    if watermarked and os.path.exists(final_pdf):
        os.remove(final_pdf)
    if ka != final_pdf and os.path.exists(ka):
        os.remove(ka)
    elif os.path.exists(ka):
        os.remove(ka)
    if local_thumb and os.path.exists(local_thumb):
        os.remove(local_thumb)
    time.sleep(3)


def decrypt_file(file_path, key):  
    if not os.path.exists(file_path): 
        return False  

    with open(file_path, "r+b") as f:  
        num_bytes = min(28, os.path.getsize(file_path))  
        with mmap.mmap(f.fileno(), length=num_bytes, access=mmap.ACCESS_WRITE) as mmapped_file:  
            for i in range(num_bytes):  
                mmapped_file[i] ^= ord(key[i]) if i < len(key) else i 
    return True  

async def download_and_decrypt_video(url, cmd, name, key):  
    video_path = await download_video(url, cmd, name)  
    
    if video_path:  
        decrypted = decrypt_file(video_path, key)  
        if decrypted:  
            print(f"File {video_path} decrypted successfully.")  
            return video_path  
        else:  
            print(f"Failed to decrypt {video_path}.")  
            return None  

async def send_vid(bot: Client, m: Message, cc, filename, vidwatermark, thumb, name, prog, channel_id):
    import uuid
    # Use a safe temp name for thumbnail (avoid Hindi/spaces breaking ffmpeg)
    safe_thumb = f"thumb_{uuid.uuid4().hex}.jpg"
    subprocess.run(
        f'ffmpeg -i "{filename}" -ss 00:00:10 -vframes 1 "{safe_thumb}"',
        shell=True, timeout=60
    )
    await prog.delete(True)
    reply1 = await bot.send_message(channel_id, f"**📩 Uploading Video 📩:-**\n<blockquote>**{name}**</blockquote>")
    reply = await m.reply_text(f"**Generate Thumbnail:**\n<blockquote>**{name}**</blockquote>")

    w_filename = filename  # default: no watermark
    local_thumb = None     # local thumb file if downloaded from URL

    try:
        # Resolve thumbnail
        if thumb == "/d":
            thumbnail = safe_thumb if os.path.exists(safe_thumb) else None
        elif thumb.startswith("http://") or thumb.startswith("https://"):
            # Download URL thumb to local file
            local_thumb = f"vthumb_{uuid.uuid4().hex}.jpg"
            try:
                dl = requests.get(thumb, timeout=15)
                with open(local_thumb, "wb") as tf:
                    tf.write(dl.content)
                thumbnail = local_thumb
            except Exception:
                thumbnail = safe_thumb if os.path.exists(safe_thumb) else None
        else:
            thumbnail = thumb if os.path.exists(thumb) else (safe_thumb if os.path.exists(safe_thumb) else None)

        # Apply video watermark
        if vidwatermark != "/d":
            w_filename = f"wm_{uuid.uuid4().hex}.mp4"
            font_path = "vidwater.ttf"
            result = subprocess.run(
                f'ffmpeg -y -i "{filename}" '
                f'-vf "drawtext=fontfile={font_path}:text=\'{vidwatermark}\':'
                f'fontcolor=white@0.3:fontsize=h/14:'
                f'x=w-text_w-20:y=20" '
                f'-codec:a copy "{w_filename}"',
                shell=True, timeout=600
            )
            if result.returncode != 0 or not os.path.exists(w_filename):
                # Watermark failed, use original
                w_filename = filename

    except subprocess.TimeoutExpired:
        await m.reply_text("⚠️ Watermark timed out, uploading without watermark.")
        w_filename = filename
    except Exception as e:
        await m.reply_text(f"⚠️ Watermark error: {str(e)[:200]}")
        w_filename = filename

    dur = int(duration(w_filename))
    start_time = time.time()

    try:
        await bot.send_video(
            channel_id, w_filename, caption=cc,
            supports_streaming=True, height=720, width=1280,
            thumb=thumbnail, duration=dur,
            progress=progress_bar, progress_args=(reply, start_time)
        )
    except Exception:
        await bot.send_document(
            channel_id, w_filename, caption=cc,
            progress=progress_bar, progress_args=(reply, start_time)
        )

    # Cleanup
    if w_filename != filename and os.path.exists(w_filename):
        os.remove(w_filename)
    await reply.delete(True)
    await reply1.delete(True)
    if os.path.exists(safe_thumb):
        os.remove(safe_thumb)
    if local_thumb and os.path.exists(local_thumb):
        os.remove(local_thumb)
