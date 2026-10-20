import base64
import re
import asyncio
import aiohttp
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant, Forbidden, PeerIdInvalid, ChatAdminRequired, FloodWait
from datetime import datetime, timedelta
from pyrogram import errors
from config import URL_SHORTENERS

async def shorten_url(long_url: str, client=None) -> str:
    """
    Shorten URL using configured URL shortener services
    Returns shortened URL or original URL if shortening fails
    """
    providers = getattr(client, 'url_shorteners', URL_SHORTENERS)
    for provider_key, provider_config in providers.items():
        if not provider_config.get('active', False):
            continue
            
        try:
            api_url = provider_config['api_url']
            api_token = provider_config.get('api_token', '')
            format_param = provider_config.get('format', 'text')
            
            params = {
                'api': api_token,
                'url': long_url,
                'format': format_param
            }
            params.update(provider_config.get('extra_params', {}))
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params, timeout=10) as response:
                    if response.status == 200:
                        body = (await response.text()).strip()
                        if body.startswith(('http://', 'https://')):
                            return body
                        # Some providers wrap their short URL in a JSON response.
                        try:
                            payload = await response.json(content_type=None)
                            candidates = [payload]
                            while candidates:
                                item = candidates.pop(0)
                                if isinstance(item, dict):
                                    for key, value in item.items():
                                        if key.lower() in ('shortenedurl', 'short_url', 'shorturl', 'url', 'link') and isinstance(value, str):
                                            if value.startswith(('http://', 'https://')):
                                                return value
                                        elif isinstance(value, (dict, list)):
                                            candidates.append(value)
                                elif isinstance(item, list):
                                    candidates.extend(item)
                        except Exception:
                            pass
        except Exception as e:
            print(f"Error with {provider_key}: {e}")
            continue
    
    # If all providers fail, return original URL
    return long_url

async def encode(string):
    string_bytes = string.encode("utf-8")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

async def decode(base64_string):
    base64_string = base64_string.strip("=") # links generated before this commit will be having = sign, hence striping them to handle padding errors.
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes) 
    string = string_bytes.decode("utf-8")
    return string

import secrets as _secrets
import string as _string

def generate_token(length: int = 14) -> str:
    """Generate a cryptographically secure random token (URL-safe, alphanumeric only)."""
    alphabet = _string.ascii_letters + _string.digits  # a-z A-Z 0-9
    return ''.join(_secrets.choice(alphabet) for _ in range(length))

def is_token_format(s: str) -> bool:
    """Check if string looks like a new-style token (alphanumeric, 12-16 chars, no special chars)."""
    return s.isalnum() and 12 <= len(s) <= 16


async def get_messages(client, message_ids, chat_id=None):
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temb_ids = message_ids[total_messages:total_messages+200]
        msgs = []
        try:
            msgs = await client.get_messages(
                chat_id=chat_id if chat_id else int(client.db),
                message_ids=temb_ids
            )
        except FloodWait as e:
            await asyncio.sleep(e.x)
            msgs = await client.get_messages(
                chat_id=chat_id if chat_id else int(client.db),
                message_ids=temb_ids
            )
        # Removed generic except block to see errors
        
        total_messages += len(temb_ids)
        messages.extend(msgs)
    return messages

async def get_message_id(client, message):
    # Build set of all valid DB channel IDs (primary + extras from settings)
    primary_db_id = getattr(client, 'db_channel_id', None) or int(client.db)
    try:
        extra_channels = await client.mongodb.get_db_channels()
    except Exception:
        extra_channels = []
    all_db_ids = {primary_db_id, *[int(ch) for ch in extra_channels]}
    primary_channel = getattr(client, 'db_channel', None)

    if message.forward_from_chat:
        if message.forward_from_chat.id in all_db_ids:
            return message.forward_from_message_id, message.forward_from_chat.id
        else:
            return 0, 0
    elif message.forward_sender_name:
        return 0, 0
    elif message.text:
        pattern = r"https://t.me/(?:c/)?(.*)/(\d+)"
        matches = re.match(pattern, message.text)
        if not matches:
            return 0, 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit():
            numeric_id = int(f"-100{channel_id}")
            if numeric_id in all_db_ids:
                return msg_id, numeric_id
        else:
            if primary_channel and channel_id == getattr(primary_channel, 'username', None):
                return msg_id, primary_db_id
            for ch in all_db_ids:
                try:
                    chat = await client.get_chat(ch)
                    if hasattr(chat, 'username') and chat.username == channel_id:
                        return msg_id, ch
                except Exception:
                    continue
    return 0, 0


def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time

async def is_bot_admin(client, channel_id):
    try:
        bot = await client.get_chat_member(channel_id, "me")
        if bot.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            # Check for specific rights if needed, but for DB channel, just being admin is usually enough to read/copy.
            # However, to be safe, we might want rights to post messages if we ever use it for that.
            # For now, basic admin check is fine for "reading" files.
            return True, None
        return False, "Bot is not an admin in the channel."
    except UserNotParticipant:
        return False, "Bot is not in the channel."
    except errors.ChatAdminRequired:
        return False, "Bot lacks permission to access admin information in this channel."
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

async def check_subscription(client, user_id):
    """Check if a user is subscribed to all required channels/groups."""
    statuses = {}

    for channel_id, channel_info in client.fsub_dict.items():
        channel_name = channel_info[0] if len(channel_info) > 0 else f"Channel {channel_id}"
        request = channel_info[2] if len(channel_info) > 2 else False

        if request:
            send_req = await client.mongodb.is_user_in_channel(channel_id, user_id)
            if send_req:
                statuses[channel_id] = ChatMemberStatus.MEMBER
                continue

        try:
            user = await client.get_chat_member(channel_id, user_id)
            # LEFT / BANNED count as not joined. RESTRICTED is a member in groups.
            if user.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
                statuses[channel_id] = ChatMemberStatus.BANNED
            else:
                statuses[channel_id] = user.status
                # If they are already a member in a request-mode channel, record them so future checks are instant!
                if request and user.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED):
                    try:
                        await client.mongodb.add_channel_user(channel_id, user_id)
                    except Exception:
                        pass
        except UserNotParticipant:
            statuses[channel_id] = ChatMemberStatus.BANNED
        except ChatAdminRequired:
            client.LOGGER(__name__, client.name).warning(
                f"Bot needs admin rights to check membership in {channel_name} ({channel_id})."
            )
            statuses[channel_id] = ChatMemberStatus.BANNED
        except Forbidden:
            client.LOGGER(__name__, client.name).warning(f"Bot lacks permission for {channel_name} ({channel_id}).")
            statuses[channel_id] = ChatMemberStatus.BANNED
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error checking {channel_name}: {e}")
            statuses[channel_id] = ChatMemberStatus.BANNED

    return statuses


def is_user_subscribed(statuses):
    """Check if user is subscribed to all channels/groups."""
    if not statuses:
        return False
    return all(
        status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED}
        for status in statuses.values()
    )


def force_sub(func):
    """Decorator to enforce force subscription before executing a command."""
    async def wrapper(client: Client, message: Message):
        if not client.fsub_dict:
            return await func(client, message)
        photo = client.messages.get('FSUB_PHOTO', '')
        if photo:
            try:
                msg = await message.reply_photo(
                    caption="<code>Checking subscription...</code>", 
                    photo=photo
                )
            except Exception:
                msg = await message.reply(
                    "<code>Checking subscription...</code>"
                )
        else:
            msg = await message.reply(
                "<code>Checking subscription...</code>"
            )
        user_id = message.from_user.id
        statuses = await check_subscription(client, user_id)

        if is_user_subscribed(statuses):
            try:
                await msg.delete()
            except Exception:
                pass
            # 📊 Track join count for each channel the user is verified as a member of
            import asyncio
            async def _track_joins():
                for cid, status in statuses.items():
                    if status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED):
                        try:
                            await client.mongodb.record_stat_user(cid, user_id)
                        except Exception:
                            pass
            asyncio.create_task(_track_joins())
            return await func(client, message)

        # User is not subscribed to all channels
        channel_buttons = []
        fsub_template = client.messages.get('FSUB', '')
        try:
            fsub_text = fsub_template.format(
                mention=message.from_user.mention,
                first=message.from_user.first_name,
                last=message.from_user.last_name or '',
                username=f"@{message.from_user.username}" if message.from_user.username else '',
                id=message.from_user.id
            )
        except Exception:
            fsub_text = fsub_template
        channels_message = f"{fsub_text}\n\n<b>ᴄʜᴀɴɴᴇʟ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ꜱᴛᴀᴛᴜꜱ:</b>\n\n"

        status_emojis = {
            ChatMemberStatus.MEMBER: "✅",
            ChatMemberStatus.ADMINISTRATOR: "🛡️",
            ChatMemberStatus.OWNER: "👑",
            ChatMemberStatus.RESTRICTED: "✅",
            ChatMemberStatus.BANNED: "❌",
            None: "⚠️"
        }
        c = 0
        needs_fsub_save = False
        for channel_id, channel_info in client.fsub_dict.items():
            channel_name = channel_info[0] if len(channel_info) > 0 else f"Channel {channel_id}"
            channel_link = channel_info[1] if len(channel_info) > 1 else None
            request = channel_info[2] if len(channel_info) > 2 else False
            timer = channel_info[3] if len(channel_info) > 3 else 0

            status = statuses.get(channel_id, None)
            emoji = status_emojis.get(status, "❓")
            status_of_user = "Joined" if emoji in ('✅', '🛡️', '👑') else "Not Joined"
            c += 1
            mode_tag = " [Request]" if request else ""
            channels_message += f"{c}. {emoji} <code>{channel_name}</code>{mode_tag} - __{status_of_user}__\n"

            # If timer > 0, generate dynamic timed invite link
            if timer and timer > 0:
                try:
                    expire_time = datetime.now() + timedelta(minutes=timer)
                    invite = await client.create_chat_invite_link(
                        chat_id=channel_id,
                        expire_date=expire_time,
                        creates_join_request=bool(request)
                    )
                    channel_link = invite.invite_link
                except Exception as e:
                    client.LOGGER(__name__, client.name).warning(
                        f"Failed to create timed invite link for {channel_name} ({channel_id}): {e}"
                    )

            # If permanent link is missing, generate one
            if not channel_link:
                try:
                    chat_link = await client.create_chat_invite_link(
                        chat_id=channel_id,
                        creates_join_request=bool(request)
                    )
                    channel_link = chat_link.invite_link
                    if not timer or timer <= 0:
                        client.fsub_dict[channel_id][1] = channel_link
                        needs_fsub_save = True
                except Exception as e:
                    client.LOGGER(__name__, client.name).warning(
                        f"Failed to create permanent invite link for {channel_name} ({channel_id}): {e}"
                    )
                    try:
                        chat = await client.get_chat(channel_id)
                        channel_link = getattr(chat, 'invite_link', None) or (
                            f"https://t.me/{chat.username}" if getattr(chat, 'username', None) else None
                        )
                    except Exception:
                        channel_link = None

            # Only add button for channels user has NOT joined
            if status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED}:
                btn_name = f"📩 {channel_name}" if request else f"📢 {channel_name}"
                if channel_link and isinstance(channel_link, str) and (channel_link.startswith("http://") or channel_link.startswith("https://") or channel_link.startswith("t.me/")):
                    valid_url = channel_link if channel_link.startswith("http") else f"https://{channel_link}"
                    channel_buttons.append(InlineKeyboardButton(btn_name, url=valid_url))
                else:
                    client.LOGGER(__name__, client.name).error(
                        f"Missing invite link for {channel_name} ({channel_id})! Bot must have 'Invite Users via Link' admin rights."
                    )
                    channel_buttons.append(InlineKeyboardButton(f"⚠️ {channel_name}", callback_data=f"fsub_nlink_{channel_id}"))

        if needs_fsub_save:
            try:
                await client.mongodb.save_fsub_channels(client.fsub_dict)
            except Exception:
                pass

        # Organize channel buttons in rows of 2
        keyboard = [channel_buttons[i:i + 2] for i in range(0, len(channel_buttons), 2)]

        # Add "Check Again" (instant callback) and "Try Again" (deep link)
        bot_username = getattr(client, 'username', None)
        from_link = message.text.split(" ") if message.text else []
        param = from_link[1] if len(from_link) > 1 else ""

        check_cb = f"check_sub_{param}" if param else "check_sub"
        action_row = [InlineKeyboardButton("🔄 Check Again", callback_data=check_cb)]

        if param and bot_username:
            action_row.append(InlineKeyboardButton("🔗 Try Again", url=f"https://t.me/{bot_username}/?start={param}"))
        elif bot_username:
            action_row.append(InlineKeyboardButton("🔗 Try Again", url=f"https://t.me/{bot_username}?start"))

        keyboard.append(action_row)

        buttons_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        # Edit message with status update and buttons (safely with fallback)
        try:
            if getattr(msg, 'photo', None):
                await msg.edit_caption(caption=channels_message, reply_markup=buttons_markup)
            else:
                await msg.edit_text(text=channels_message, reply_markup=buttons_markup)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error updating message: {e}. Attempting fallback reply.")
            try:
                await msg.delete()
            except Exception:
                pass
            try:
                await message.reply(text=channels_message, reply_markup=buttons_markup)
            except Exception as e2:
                client.LOGGER(__name__, client.name).error(f"Fallback reply also failed: {e2}")

    return wrapper

@Client.on_callback_query(filters.regex(r"^check_sub(?:_(.*))?$"))
async def check_sub_cb(client: Client, query: CallbackQuery):
    """Instant 1-tap re-verification callback handler for Force Sub."""
    user_id = query.from_user.id
    statuses = await check_subscription(client, user_id)

    if is_user_subscribed(statuses):
        await query.answer("✅ Verification successful! Unlocking...", show_alert=False)
        try:
            await query.message.delete()
        except Exception:
            pass

        data = query.data.split("_", 2)
        param = data[2] if len(data) > 2 and data[2] else ""

        # Construct simulated message to deliver files / invoke start command seamlessly
        from plugins.start import start_command
        simulated_msg = query.message
        simulated_msg.text = f"/start {param}".strip()
        simulated_msg.from_user = query.from_user
        return await start_command(client, simulated_msg)
    else:
        await query.answer("❌ You haven't joined/requested all channels yet! Please check the channels above.", show_alert=True)

async def delete_files(messages, client, k, enter):
    auto_del = client.auto_del
    keyboard = None
    if auto_del > 0:
        await asyncio.sleep(auto_del)

        for msg in messages:
            if msg and msg.chat:
                try:
                    await client.delete_messages(chat_id=msg.chat.id, message_ids=[msg.id])
                except Exception as e:
                    client.LOGGER(__name__, client.name).warning(f"The attempt to delete the media {getattr(msg, 'id', 'Unknown')} was unsuccessful: {e}")
            else:
                client.LOGGER(__name__, client.name).warning("Encountered an empty or deleted message.")
        
        command = enter.split(" ") if enter else []
        command_part = command[1] if len(command) > 1 else None
        
        if command_part:
            url = f"https://t.me/{client.username}?start={command_part}"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", url=url)]
            ])
            
    await k.edit_text(
        "<blockquote><b><i>Your Video / File Is Successfully Deleted ✅</i></b></blockquote>",
        reply_markup=keyboard
    )
