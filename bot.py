import os
import asyncio
import re
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
ADMIN_ID = 6056498996
BOT_TOKEN = "7417509437:AAGDojH2poJLfqwjcy5MyOy8aivMb-MUGGY"
API_ID = 27936544 
API_HASH = "b0a342a9883d22fef6910fbef428a760"

# API Endpoints (Remote URL Upload)
LULU_API = "https://lulustream.com/api/upload/url?key=96407rehqnrwk0bm3o2p&url={url}"
EARN_API = "https://earnvidsapi.com/api/upload/url?key=30245moj897ilunshbh1b&url={url}"

# Target Bypass Bot
BYPASS_BOT = "DD_Bypass_Bot"

# Track tasks: {forwarded_msg_id: {"chat_id": int, "original_msg_id": int, "status_msg_id": int}}
active_tasks = {}

app = Client("NkbFinalBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- HELPER: REMOTE UPLOAD ---
async def call_api(url_template, target_url):
    api_url = url_template.format(url=target_url)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, timeout=15) as resp:
                data = await resp.json()
                # Extract filecode from result
                res = data.get("result")
                return res if isinstance(res, str) else res.get("filecode")
        except:
            return None

# --- ADMIN COMMAND (/nk19) ---
@app.on_message(filters.command("nk19") & filters.user(ADMIN_ID))
async def admin_panel(client, message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Bot Status: ✅ Online", callback_data="none")],
        [InlineKeyboardButton("Check API Balance", callback_data="none")]
    ])
    await message.reply("🛠 **Admin Control Panel**", reply_markup=kb)

# --- USER COMMAND (/nkw) ---
@app.on_message(filters.command("nkw") & filters.reply)
async def nkw_handler(client, message):
    reply = message.reply_to_message
    if not (reply.video or reply.document):
        return await message.reply("❌ Reply to a video or file.")

    status = await message.reply("⏳ Syncing with Bypass Bot...")
    
    # Forward file to bypass bot
    try:
        forwarded = await reply.forward(BYPASS_BOT)
        active_tasks[forwarded.id] = {
            "chat_id": message.chat.id,
            "status_msg_id": status.id,
            "original_msg": reply
        }
    except Exception as e:
        await status.edit_text(f"❌ Error forwarding: {e}")

# --- BYPASS BOT RESPONSE HANDLER ---
@app.on_message(filters.chat(BYPASS_BOT))
async def bypass_listener(client, message):
    # Match the reply to our forwarded message
    if not (message.reply_to_message and message.reply_to_message.id in active_tasks):
        return

    task = active_tasks.pop(message.reply_to_message.id)
    chat_id = task["chat_id"]

    # Extract URL from text or buttons
    search_text = message.text or ""
    if message.reply_markup:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url: search_text += f" {btn.url}"
    
    urls = re.findall(r'https?://\S+', search_text)
    if not urls:
        return await client.send_message(chat_id, "❌ Failed to get DL link from Bypass Bot.")

    dl_link = urls[0]
    await client.edit_message_text(chat_id, task["status_msg_id"], "📡 DL Link Found! Uploading to Lulu & Earn...")

    # Remote Upload
    l_code, e_code = await asyncio.gather(
        call_api(LULU_API, dl_link),
        call_api(EARN_API, dl_link)
    )

    l_link = f"https://lulustream.com/{l_code}" if l_code else "❌ Failed"
    e_link = f"https://earnvids.com/{e_code}" if e_code else "❌ Failed"

    # Send the output
    # 1. Send the original file (One-click file sending)
    sent_file = await task["original_msg"].copy(chat_id)
    
    # 2. Send the links
    final_msg = await client.send_message(
        chat_id,
        f"✅ **File Synced Successfully!**\n\n"
        f"🔗 **Lulustream:** {l_link}\n"
        f"🔗 **Earnvids:** {e_link}\n\n"
        f"🕒 *Auto-deleting in 5 minutes.*",
        disable_web_page_preview=True
    )

    await client.delete_messages(chat_id, task["status_msg_id"])

    # --- AUTO DELETE (5 MINUTES) ---
    await asyncio.sleep(300)
    try:
        await sent_file.delete()
        await final_msg.delete()
    except:
        pass

if __name__ == "__main__":
    print("Bot Started Successfully!")
    app.run()
