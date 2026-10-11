from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.helper_func import encode, get_message_id
from helper.font_converter import to_small_caps as sc
import humanize
import io

async def get_db_channels_info(client):
    """Get formatted database channels information with links"""
    primary_db = getattr(client, 'db_channel_id', None) or int(client.db)
    try:
        extra_channels = await client.mongodb.get_db_channels()
    except Exception:
        extra_channels = []
    
    if not extra_channels:
        try:
            primary_chat = getattr(client, 'db_channel', None) or await client.get_chat(primary_db)
            if hasattr(primary_chat, 'invite_link') and primary_chat.invite_link:
                return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: <a href='{primary_chat.invite_link}'>{primary_chat.title}</a></blockquote>"
            else:
                title = getattr(primary_chat, 'title', primary_db)
                return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: {title} (`{primary_db}`)</blockquote>"
        except Exception:
            return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: `{primary_db}`</blockquote>"
    
    channels_info = ["<blockquote>✦ ᴀᴠᴀɪʟᴀʙʟᴇ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs:</blockquote>"]
    all_channels = [primary_db] + [int(ch) for ch in extra_channels if int(ch) != primary_db]
    for ch_id in all_channels:
        is_primary = (ch_id == primary_db)
        is_primary_text = "✦ ᴘʀɪᴍᴀʀʏ" if is_primary else "• sᴇᴄᴏɴᴅᴀʀʏ"
        try:
            chat = await client.get_chat(ch_id)
            if hasattr(chat, 'invite_link') and chat.invite_link:
                channels_info.append(f"{is_primary_text}: <a href='{chat.invite_link}'>{chat.title}</a>")
            else:
                channels_info.append(f"{is_primary_text}: {getattr(chat, 'title', ch_id)} (`{ch_id}`)")
        except Exception:
            channels_info.append(f"{is_primary_text}: `{ch_id}`")
            
    return "\n".join(channels_info)

# ==================== BATCH COMMAND ====================
@Client.on_message(filters.private & filters.command('batch'))
async def batch(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    db_channels_info = await get_db_channels_info(client)
    
    while True:
        try:
            first_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ꜰɪʀsᴛ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>
{db_channels_info}

<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception:
            return
            
        f_msg_id, source_channel_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply("<blockquote>✗ ᴇʀʀᴏʀ</blockquote>\n\nᴛʜɪs ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ɪs ɴᴏᴛ ꜰʀᴏᴍ ᴍʏ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴏʀ ᴛʜɪs ʟɪɴᴋ ɪs ᴛᴀᴋᴇɴ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ", quote=True)
            continue

    while True:
        try:
            second_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ʟᴀsᴛ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>
{db_channels_info}

<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception:
            return
            
        s_msg_id, _ = await get_message_id(client, second_message)
        if s_msg_id:
            break
        else:
            await second_message.reply("<blockquote>✗ ᴇʀʀᴏʀ</blockquote>\n\nᴛʜɪs ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ɪs ɴᴏᴛ ꜰʀᴏᴍ ᴍʏ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴏʀ ᴛʜɪs ʟɪɴᴋ ɪs ᴛᴀᴋᴇɴ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ", quote=True)
            continue

    # Algorithm based hash encoding
    string = f"get-{f_msg_id * abs(source_channel_id)}-{s_msg_id * abs(source_channel_id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 sʜᴀʀᴇ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}')]])
    
    info_text = f"<blockquote><b>📦 {sc('batch link created')}</b>\n🔢 {sc('range')}: {f_msg_id} - {s_msg_id}"
    if client.auto_del > 0:
        info_text += f"\n⏳ {sc('auto delete')}: {humanize.naturaldelta(client.auto_del)}"
    info_text += "</blockquote>\n\n"
    
    await second_message.reply_text(f"{info_text}<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀᴛᴄʜ ʟɪɴᴋ</blockquote>\n\n<code>{link}</code>", quote=True, disable_web_page_preview=True, reply_markup=reply_markup)


# ==================== GENLINK COMMAND ====================
@Client.on_message(filters.private & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    main_channel = getattr(client, 'db_channel_id', None) or int(client.db)

    # Shortcut: If replied to a message, copy/link it directly
    if message.reply_to_message:
        replied = message.reply_to_message
        processing_msg = await message.reply(f"🔄 {sc('processing')}...")
        try:
            f_msg_id, source_channel_id = await get_message_id(client, replied)
            if not f_msg_id:
                post = await replied.copy(chat_id=main_channel, caption=replied.caption)
                f_msg_id = post.id
                source_channel_id = main_channel

            file_name = ""
            if replied.document:
                file_name = replied.document.file_name or ""
            elif replied.caption:
                file_name = replied.caption.split("\n")[0][:50]
            elif replied.text:
                file_name = replied.text[:50]

            base64_string = await encode(f"get-{f_msg_id * abs(source_channel_id)}")
            link = f"https://t.me/{client.username}?start={base64_string}"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"🔁 {sc('share url')}", url=f'https://telegram.me/share/url?url={link}')]])

            text = "<blockquote>"
            if file_name:
                text += f"<b>📂 {file_name}</b>\n"
            if client.auto_del > 0:
                text += f"⏳ {sc('auto delete')}: {humanize.naturaldelta(client.auto_del)}"
            if text == "<blockquote>":
                text = ""
            else:
                text += "</blockquote>\n\n"
            text += f"<b>{sc('here is your link')}</b>\n\n<code>{link}</code>"

            await processing_msg.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            await processing_msg.edit_text(f"❌ {sc('error')}: {e}")
        return

    # Interactive flow
    db_channels_info = await get_db_channels_info(client)
    while True:
        try:
            channel_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>
{db_channels_info}

<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception:
            return
            
        msg_id, source_channel_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        else:
            await channel_message.reply("<blockquote>✗ ᴇʀʀᴏʀ</blockquote>\n\nᴛʜɪs ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ɪs ɴᴏᴛ ꜰʀᴏᴍ ᴍʏ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴏʀ ᴛʜɪs ʟɪɴᴋ ɪs ɴᴏᴛ ᴛᴀᴋᴇɴ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ", quote=True)
            continue

    base64_string = await encode(f"get-{msg_id * abs(source_channel_id)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 sʜᴀʀᴇ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}')]])
    await channel_message.reply_text(f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ</blockquote>\n\n<code>{link}</code>", quote=True, disable_web_page_preview=True, reply_markup=reply_markup)


# ==================== NBATCH COMMAND ====================
@Client.on_message(filters.private & filters.command("nbatch"))
async def nbatch(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("<blockquote>✗ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ!</blockquote> ᴜsᴇ: `/nbatch {number}`")
        return
    
    batch_size = int(args[1])
    db_channels_info = await get_db_channels_info(client)
    
    while True:
        try:
            first_message = await client.ask(
                text=f"""<blockquote>🚀 sᴇɴᴅ ᴅʙ ᴄʜᴀɴɴᴇʟ ꜰɪʀsᴛ ᴍᴇssᴀɢᴇ ʟɪɴᴋ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)...</blockquote>
{db_channels_info}""",
                chat_id=message.from_user.id,
                filters=(filters.text & ~filters.forwarded),
                timeout=60
            )
        except Exception:
            return
    
        f_msg_id, source_channel_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply("<blockquote>😫 ɪɴᴠᴀʟɪᴅ!</blockquote> sᴇɴᴅ ᴄᴏʀʀᴇᴄᴛ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴍᴇssᴀɢᴇ ʟɪɴᴋ.", quote=True)
            continue
    
    s_msg_id = f_msg_id + batch_size - 1
    string = f"get-{f_msg_id * abs(source_channel_id)}-{s_msg_id * abs(source_channel_id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📫 ʏᴏᴜʀ ʙᴀᴛᴄʜ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}')]
    ])
    
    await first_message.reply_text(f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀᴛᴄʜ ʟɪɴᴋ ({batch_size} files)</blockquote>\n\n<code>{link}</code>", quote=True, disable_web_page_preview=True, reply_markup=reply_markup)


# ==================== BULK COMMAND ====================
@Client.on_message(filters.private & filters.command("bulk"))
async def bulk(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    db_channels_info = await get_db_channels_info(client)
    
    while True:
        try:
            first_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ꜰɪʀsᴛ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n{db_channels_info}\n\n<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception:
            return
        f_msg_id, source_channel_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply("<blockquote>✗ ᴇʀʀᴏʀ</blockquote>\n\nᴛʜɪs ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ɪs ɴᴏᴛ ꜰʀᴏᴍ ᴍʏ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴏʀ ᴛʜɪs ʟɪɴᴋ ɪs ᴛᴀᴋᴇɴ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ", quote=True)
            continue

    while True:
        try:
            second_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ʟᴀsᴛ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>\n{db_channels_info}\n\n<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception:
            return
        s_msg_id, _ = await get_message_id(client, second_message)
        if s_msg_id:
            break
        else:
            await second_message.reply("<blockquote>✗ ᴇʀʀᴏʀ</blockquote>\n\nᴛʜɪs ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ɪs ɴᴏᴛ ꜰʀᴏᴍ ᴍʏ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴏʀ ᴛʜɪs ʟɪɴᴋ ɪs ᴛᴀᴋᴇɴ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ", quote=True)
            continue
            
    if f_msg_id > s_msg_id:
        f_msg_id, s_msg_id = s_msg_id, f_msg_id

    processing_msg = await second_message.reply("⏳ Processing...", quote=True)
    
    msg_ids = list(range(f_msg_id, s_msg_id + 1))
    messages = []
    
    for i in range(0, len(msg_ids), 200):
        try:
            chunk = await client.get_messages(chat_id=source_channel_id, message_ids=msg_ids[i:i+200])
            for msg in chunk:
                if msg and not msg.empty:
                    messages.append(msg)
        except Exception:
            pass
    
    file_links = []
    count = 1
    for msg in messages:
        file_name = None
        if getattr(msg, "document", None):
            file_name = msg.document.file_name
        elif getattr(msg, "video", None):
            file_name = msg.video.file_name
        elif getattr(msg, "audio", None):
            file_name = msg.audio.file_name
            
        if not file_name:
            if msg.media:
                file_name = f"Unknown_Media_{msg.id}"
            else:
                continue
            
        base64_string = await encode(f"get-{msg.id * abs(source_channel_id)}")
        link = f"https://t.me/{client.username}?start={base64_string}"
        file_links.append(f"{count}. {file_name} - {link}")
        count += 1
        
    db_key = str(source_channel_id)[-4:] if len(str(source_channel_id)) >= 4 else str(source_channel_id)
        
    batch_string = f"get-{f_msg_id * abs(source_channel_id)}-{s_msg_id * abs(source_channel_id)}"
    base64_batch = await encode(batch_string)
    batch_link = f"https://t.me/{client.username}?start={base64_batch}"
        
    final_text = f"📦 Bulk Upload Complete\n\nTotal Files: {len(file_links)}\nDB Key: {db_key}\n\nDownload URLs:\n\n"
    final_text += "\n".join(file_links)
    final_text += f"\n\n🔗 <b>Batch Link:</b> {batch_link}"
    
    if len(final_text) > 4050:
        file_bytes = io.BytesIO(final_text.encode('utf-8'))
        file_bytes.name = "bulk_links.txt"
        await second_message.reply_document(document=file_bytes, caption=f"📦 Bulk Upload Complete\nTotal Files: {len(file_links)}\nDB Key: {db_key}\n\nThe text was too long, so here is the text file.", quote=True)
        await processing_msg.delete()
    else:
        await processing_msg.edit_text(final_text, disable_web_page_preview=True)


# ==================== SINGLE FILE UPLOAD IN PM ====================
@Client.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo) & ~filters.command(["start", "batch", "nbatch", "genlink", "bulk", "settings", "help"]))
async def single_file_gen_handler(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return

    if message.text and message.text.startswith("/"):
        return

    try:
        msg = await message.reply(f"🔄 {sc('processing')}...", quote=True)
        main_channel = getattr(client, 'db_channel_id', None) or int(client.db)
        
        f_msg_id, source_channel_id = await get_message_id(client, message)
        if not f_msg_id:
            # Copy to primary or next DB channel
            try:
                channel_id = await client.mongodb.get_next_db_channel(main_channel)
            except Exception:
                channel_id = main_channel
            post = await message.copy(chat_id=channel_id, caption=message.caption)
            msg_id = post.id
            source_channel_id = channel_id
        else:
            msg_id = f_msg_id

        file_name = ""
        if message.document:
            file_name = message.document.file_name or ""
        elif message.video:
            file_name = message.video.file_name or ""
        elif message.audio:
            file_name = message.audio.file_name or ""
        elif message.caption:
            file_name = message.caption.split("\n")[0][:50]

        # Algorithm based hash encoding
        converted_id = msg_id * abs(source_channel_id)
        base64_string = await encode(f"get-{converted_id}")
        link = f"https://t.me/{client.username}?start={base64_string}"
        
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"🔁 {sc('share url')}", url=f'https://telegram.me/share/url?url={link}')]])
        
        text = "<blockquote>"
        if file_name:
            text += f"<b>📂 {file_name}</b>\n"
        if client.auto_del > 0:
            text += f"⏳ {sc('auto delete')}: {humanize.naturaldelta(client.auto_del)}"
        if text == "<blockquote>":
            text = ""
        else:
            text += "</blockquote>\n\n"

        text += f"<b>{sc('here is your link')}</b>\n\n<code>{link}</code>"
        await msg.edit_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        await message.reply(f"❌ {sc('error')}: {e}")
