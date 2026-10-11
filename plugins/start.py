# Made by @Awakeners_Bots
# GitHub: https://github.com/Awakener_Bots

from helper.helper_func import *
from helper.credit_db import credit_db
from helper.enhanced_credit_db import EnhancedCreditDB
from helper.font_converter import to_small_caps as sc
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import humanize
import secrets
import json

# Load credit configuration
try:
    with open("setup.json", "r") as f:
        setup_data = json.load(f)
        credit_config = setup_data[0].get("credit_config", {})
except:
    credit_config = {}


@Client.on_message(filters.command('start') & filters.private)
@force_sub
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    present = await client.mongodb.present_user(user_id)
    if not present:
        try:
            await client.mongodb.add_user(user_id)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error adding a user:\n{e}")

    is_banned = await client.mongodb.is_banned(user_id)
    if is_banned:
        return await message.reply(f"**{sc('You have been banned from using this bot!')}**")
    
    # Premium check
    is_premium_user = await client.mongodb.is_premium(user_id)

    # Enhanced credit system
    enhanced_db = EnhancedCreditDB(client.db_uri, client.db_name)
    credit_data = await enhanced_db.get_credits(user_id)
    user_credits = credit_data.get("balance", 0)
    
    # Check for expired credits
    await enhanced_db.check_and_remove_expired(user_id)

    text = message.text
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1].strip()
        except IndexError:
            return

        # Early return removed to allow valid handling of batch links

        
        # ============== REFERRAL SYSTEM ==============
        # Check if this is a referral link: /start ref_XXXXXXXX
        if base64_string.startswith("ref_"):
            referral_code = base64_string.replace("ref_", "")
            
            # Apply referral if user is new
            if not present:
                referrer_id = await enhanced_db.apply_referral(user_id, referral_code)
                if referrer_id:
                    # Notify new user
                    await message.reply(
                        f"🎉 **{sc('Welcome!')}**\n\n"
                        f"{sc('You joined using a referral link!')}\n"
                        f"{sc('When you access your first file, your referrer will earn credits!')}"
                    )
            return
            
        access_token = None
        original_base64 = base64_string
        
        # ---------------- TOKEN VERIFIED / SHORTENER SOLVED ----------------
        if "_" in base64_string:
            parts = base64_string.split("_", 1)
            # Handle batch_ID_TOKEN case where batch_ID might contain underscores? 
            # No, batch_ID is hex. So splitting logic works.
            # But wait, create_batch uses secrets.token_hex(8) -> "a1b2c3d4e5f6g7h8" (no underscores)
            # So splitting by first "_" is fine if token is second part.
            # BUT if original was "batch_XYZ", split gives "batch", "XYZ". 
            # NO. "batch_XYZ_TOKEN". 
            # split("_", 1) -> "batch", "XYZ_TOKEN". WRONG.
            # We need to handle "batch_" prefix carefully.
            
            # If it starts with batch_, we assume format: batch_BATCHID_TOKEN
            if base64_string.startswith("batch_"):
                # expected: batch_{id}_{token}
                # split("_") -> [batch, id, token]
                parts = base64_string.split("_")
                if len(parts) >= 3:
                     # reconstruct original: batch_{id}
                     original_base64 = f"{parts[0]}_{parts[1]}"
                     access_token = parts[2]
                else:
                    # Fallback or invalid
                    pass
            elif len(parts) == 2:
                original_base64 = parts[0]
                access_token = parts[1]

            if access_token:
                # Check if verification is enabled
                token_verification_enabled = await client.mongodb.get_bot_config('token_verification_enabled', True)

                # ONLY Verify if enabled
                if token_verification_enabled:
                    # Track shortener click
                    await client.mongodb.increment_token_clicks(user_id, access_token)

                    verify_result = await client.mongodb.verify_access_token(
                        user_id, access_token, original_base64
                    )
    
                    # ======================= ANTI-BYPASS LOGIC ======================
                    if verify_result == "BYPASS":
                        # Check for auto-ban (Skip for Admins)
                        if user_id not in client.admins:
                            was_banned = await client.mongodb.check_and_auto_ban(user_id, max_attempts=5)
                            
                            if was_banned:
                                await message.reply(
                                    f"<blockquote>🚫 <b>{sc('you have been banned')}</b></blockquote>\n"
                                    f"<blockquote><b>{sc('reason: multiple bypass attempts detected')}</b></blockquote>\n"
                                    f"<blockquote><b>{sc('contact admin if you think this is a mistake')}</b></blockquote>"
                                )
                                return
                        
                        await message.reply(
                            f"<blockquote>⚠️ <b>{sc('bypass detected')}</b></blockquote>\n"
                            f"<blockquote><b>{sc('how many times have i told you, dont try to outsmart your dad')}🖕</b></blockquote>\n"
                            f"<blockquote><b>{sc('now be a good boy and solve it again, and this time dont get smart !!')}</b></blockquote>"
                        )
    
                        # Notify admin
                        bypass_count = await client.mongodb.get_bypass_count(user_id)
                        await client.send_message(
                            client.owner,
                            f"🚨 <b>{sc('bypass detected')}</b>\n"
                            f"{sc('user')}: <code>{user_id}</code>\n"
                            f"{sc('attempts in 24h')}: <b>{bypass_count}</b>"
                        )
                        return
                    
                    # Handle other error cases
                    if verify_result == "ALREADY_USED":
                        await message.reply(
                            f"<blockquote>❌ <b>{sc('token already used')}</b></blockquote>\n"
                            f"<blockquote><b>{sc('this link can only be used once')}</b></blockquote>\n"
                            f"<blockquote><b>{sc('please get a new link')}</b></blockquote>"
                        )
                        return
                    
                    if verify_result == "EXPIRED":
                        await message.reply(
                            f"<blockquote>⏰ <b>{sc('token expired')}</b></blockquote>\n"
                            f"<blockquote><b>{sc('this link has expired')}</b></blockquote>\n"
                            f"<blockquote><b>{sc('please get a new link')}</b></blockquote>"
                        )
                        return
    
                    if verify_result != "OK":
                        await message.reply(
                            f"<blockquote>❌ <b>{sc('invalid token')}</b></blockquote>\n"
                            f"<blockquote><b>{sc('please get a new link')}</b></blockquote>"
                        )
                        return
    
                    # ---------------- GIVE 3 CREDITS (IF ENABLED) ----------------
                    credit_system_enabled = await client.mongodb.is_credit_system_enabled()
                    
                    if credit_system_enabled:
                        expiry_days = credit_config.get("expiry_days", 30)
                        verification_reward = await client.mongodb.get_bot_config('verification_reward', 3)
                        await enhanced_db.add_credits(user_id, verification_reward, expiry_days, reason="shortener_solved")

                        # Re-fetch credits to ensure accurate count for deduction
                        credit_data = await enhanced_db.get_credits(user_id)
                        user_credits = credit_data.get("balance", 0)
    
                        await message.reply(
                            f"<b>🎉 {sc('verification successful!')}</b>\n"
                            f"✅ <b>{sc(f'you earned {verification_reward} credits!')}</b>\n"
                            f"📂 <b>{sc('sending your file now...')}</b>"
                        )
                    else:
                        await message.reply(
                            f"<b>🎉 {sc('verification successful!')}</b>\n"
                            f"📂 <b>{sc('sending your file now...')}</b>"
                        )

                    # Grant temporary access to bypass the check below
                    is_premium_user = True
                    
                    # If this was a BATCH link, we need to manually trigger the batch handler
                    if original_base64.startswith("batch_"):
                         batch_id = original_base64.replace("batch_", "").strip()
                         from plugins.batch_handler import process_batch
                         await process_batch(client, message, batch_id)
                         message.stop_propagation()
                         return

                    # Fall through to file sending logic...

        # -------------------------- ALGORITHM BASE64 / TOKEN DECODE --------------------------
        ids = []
        custom_chat_id = None

        if original_base64.startswith("batch_"):
            # Raw Batch Link: handled by batch_handler
            ids = []
            custom_chat_id = None
        else:
            decoded_success = False
            try:
                string = await decode(original_base64)
                argument = string.split("-")
                
                primary_db = getattr(client, 'db_channel_id', None) or int(client.db)
                all_db_channels = [primary_db]
                try:
                    extra_channels = await client.mongodb.get_db_channels()
                    all_db_channels.extend([int(c) for c in extra_channels if int(c) != primary_db])
                except Exception:
                    pass

                if len(argument) == 3:
                    encoded_start = int(argument[1])
                    encoded_end = int(argument[2])
                    source_channel_id = None
                    
                    for ch_id in all_db_channels:
                        mult = abs(ch_id)
                        if encoded_start % mult == 0 and encoded_end % mult == 0:
                            source_channel_id = ch_id
                            start = int(encoded_start / mult)
                            end = int(encoded_end / mult)
                            break
                    
                    if source_channel_id is None:
                        source_channel_id = primary_db
                        start = int(encoded_start / abs(primary_db))
                        end = int(encoded_end / abs(primary_db))

                    ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
                    custom_chat_id = source_channel_id
                    decoded_success = True

                elif len(argument) == 2:
                    encoded_msg = int(argument[1])
                    source_channel_id = None
                    
                    for ch_id in all_db_channels:
                        mult = abs(ch_id)
                        if encoded_msg % mult == 0:
                            source_channel_id = ch_id
                            ids = [int(encoded_msg / mult)]
                            break
                            
                    if source_channel_id is None:
                        source_channel_id = primary_db
                        ids = [int(encoded_msg / abs(primary_db))]
                    custom_chat_id = source_channel_id
                    decoded_success = True
            except Exception:
                decoded_success = False

            # Backward compatibility fallback for MongoDB tokens
            if not decoded_success:
                from helper.helper_func import is_token_format
                if is_token_format(original_base64):
                    token_doc = await client.mongodb.resolve_file_token(original_base64)
                    if token_doc:
                        channel_id = token_doc["channel_id"]
                        start_msg_id = token_doc["msg_id"]
                        end_msg_id = token_doc.get("end_msg_id")
                        ids = list(range(start_msg_id, end_msg_id + 1)) if end_msg_id else [start_msg_id]
                        custom_chat_id = channel_id
                        decoded_success = True
                    else:
                        return await message.reply(
                            f"<blockquote>❌ <b>{sc('invalid or expired link')}</b></blockquote>\n"
                            f"<blockquote><b>{sc('please get a new link')}</b></blockquote>"
                        )
                else:
                    return await message.reply("⚠️ Invalid or expired link.")

        
        # Check if credit system is enabled globally
        credit_system_enabled = await client.mongodb.is_credit_system_enabled()
        
        # Check if token verification is enabled
        token_verification_enabled = await client.mongodb.get_bot_config('token_verification_enabled', True)
        
        # ------------------ USER TRYING TO GET FILE ------------------
        
        # Check if this is user's first file access (for referral reward)
        is_first_file = credit_data.get("total_spent", 0) == 0 and not is_premium_user

        # If user has credits → deduct ONE (ONLY IF SYSTEM ENABLED)
        if credit_system_enabled and user_credits > 0 and not is_premium_user:
            await enhanced_db.use_credit(user_id)
            user_credits -= 1
            is_premium_user = True

            await message.reply(
                f"⚡ {sc('1 credit used')}!\n"
                f"{sc('remaining credits')}: {user_credits}"
            )
            
            # Reward referrer if this is first file access
            if is_first_file and credit_data.get("referred_by"):
                # ... (existing code) ...
                
                # Notify referrer
                try:
                    await client.send_message(
                        referrer_id,
                        f"🎉 **{sc('referral reward')}!**\n\n"
                        f"{sc('you earned')} **{reward_amount} {sc('credits')}** {sc('for referring a user')}!\n"
                        f"{sc('user id')}: <code>{user_id}</code>\n\n"
                        f"{sc('keep sharing your referral link to earn more!')}"
                    )
                except:
                    pass

        # If STILL not premium → show shortener (ONLY IF ENABLED)
        if not is_premium_user and token_verification_enabled:
            temp_msg = await message.reply(f"🔄 **{sc('generating your link')}...**")
            
            # ---------------- FETCH CONTENT NAME ----------------
            content_name = ""
            try:
                if original_base64.startswith("batch_"):
                    b_id = original_base64.replace("batch_", "").strip()
                    batch = await client.mongodb.get_batch(b_id)
                    if batch:
                        content_name = f"📦 <b>{batch.get('base_name', 'Batch Pack')}</b>\n\n"
                elif 'ids' in locals() and ids:
                    # Use resolved IDs (Works for Token & Old Base64)
                    try:
                        t_msg_id = ids[0]
                        t_chat_id = custom_chat_id if 'custom_chat_id' in locals() and custom_chat_id else client.db
                        
                        # Fetch message
                        f_msg = await client.get_messages(t_chat_id, t_msg_id)
                        if f_msg:
                            if f_msg.document:
                                content_name = f"🎬 <b>{f_msg.document.file_name}</b>\n\n"
                            elif f_msg.caption:
                                # Start of caption usually contains filename or title
                                pass 
                    except:
                        pass
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Error fetching content name: {e}")
            
            access_token = secrets.token_hex(16)
            await client.mongodb.create_access_token(user_id, original_base64, access_token)
            
            file_link = f"https://t.me/{client.username}?start={original_base64}_{access_token}"
            shortened_url = await shorten_url(file_link)
            
            await temp_msg.delete()
            
            premium_text = (
                f"{content_name}"
                f"<b>🔗 {sc('your file link')}:</b>\n\n"
                f"<blockquote>👉 {sc('solve the shortener to unlock your file')}</blockquote>\n\n"
                f"<b>💎 {sc('want direct access')}?</b> {sc('buy premium')}!"
            )
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"⌜{sc('get files')}⌟", url=shortened_url)],
                [
                    InlineKeyboardButton(f"「{sc('tutorial')}」", url="https://t.me/+rKJmAabX6MxmMjg9"),
                    InlineKeyboardButton(f"「{sc('premium')}」", url="https://t.me/Cultured_Support_bot")
                ]
            ])
            
            await client.send_photo(
                chat_id=message.chat.id,
                photo="https://i.ibb.co/FtnfS25/photo-2025-10-31-18-43-10-7567458335163678756.jpg",
                caption=premium_text,
                reply_markup=buttons,
                protect_content=True
            )
            if original_base64.startswith("batch_"):
                message.stop_propagation()
            return
        
        # ------------------ PREMIUM / CREDIT USERS: SEND FILE ------------------
        
        if original_base64.startswith("batch_"):
             batch_id = original_base64.replace("batch_", "").strip()
             from plugins.batch_handler import process_batch
             await process_batch(client, message, batch_id)
             message.stop_propagation()
             return

        temp_msg = await message.reply(f"{sc('wait a sec')}..")
        
        try:
            if 'custom_chat_id' in locals() and custom_chat_id:
                # Multi-DB Fetch
                messages = await get_messages(client, ids, custom_chat_id)
            else:
                # Default DB Fetch
                messages = await get_messages(client, ids)
        except:
            await temp_msg.edit_text(f"{sc('something went wrong')}..!")
            return
        finally:
            if messages:
                await temp_msg.delete()
            else:
                await temp_msg.edit(f"{sc('couldnt find the files in database')}.")

        yugen_msgs = []

        for msg in messages:
            caption = (
                client.messages.get('CAPTION', '').format(
                    previouscaption=f"<blockquote>{msg.caption.html}</blockquote>" if msg.caption else f"<blockquote>{msg.document.file_name}</blockquote>"
                )
                if client.messages.get('CAPTION', '') and msg.document
                else (msg.caption.html if msg.caption else "")
            )

            try:
                copied_msg = await msg.copy(
                    chat_id=user_id,
                    caption=caption,
                    protect_content=client.protect
                )
                yugen_msgs.append(copied_msg)
            except:
                pass

        if messages and client.auto_del > 0:
            warning = await client.send_message(
                user_id,
                f"<b>⚠️ {sc('file will be deleted in')} {humanize.naturaldelta(client.auto_del)}.</b>"
            )
            asyncio.create_task(delete_files(yugen_msgs, client, warning, text))
        return

    # ---------------- NORMAL /start UI ----------------
    buttons = [
        [InlineKeyboardButton("⌜UPDATES⌟", url="https://t.me/toonworld4all_Tamil"),
         InlineKeyboardButton("⌜ɴᴇᴛᴡᴏʀᴋ⌟", url="https://t.me/toonworld4all_Tamil")],
        [InlineKeyboardButton("⌜ᴀʙᴏᴜᴛ⌟", callback_data="about"),
         InlineKeyboardButton("⌜ᴅᴇᴠ⌟", url="https://t.me/toonworld4all_Tamil")]
    ]
    
    if user_id in client.admins:
        buttons.insert(0, [InlineKeyboardButton("⌜ꜱᴇᴛᴛɪɴɢꜱ⌟", callback_data="settings")])
    
    photo = client.messages.get("START_PHOTO", "")
    if photo:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=photo,
            caption=client.messages.get('START', 'No Start Msg').format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=f"@{message.from_user.username}" if message.from_user.username else None,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await client.send_message(
            chat_id=message.chat.id,
            text=client.messages.get('START', 'No Start Message').format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=f"@{message.from_user.username}" if message.from_user.username else None,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
