# Made by @Awakeners_Bots
# GitHub: https://github.com/Awakener_Bots

from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest

@Client.on_chat_join_request()
async def handle_join_request(client, join_request: ChatJoinRequest):
    user_id = join_request.from_user.id
    channel_id = join_request.chat.id
    
    is_banned = await client.mongodb.is_banned(user_id)
    if is_banned:
        return
    
    channel = client.fsub_dict.get(channel_id, [])
    if channel:
        # Track this join request so user can use the bot immediately
        await client.mongodb.add_channel_user(channel_id, user_id)
        try:
            await client.mongodb.record_stat_user(channel_id, user_id)
        except Exception:
            pass

        # Only approve the join request if auto-approve is explicitly enabled
        auto_approve = await client.mongodb.is_fsub_auto_approve_enabled()
        if auto_approve:
            try:
                await client.approve_chat_join_request(channel_id, user_id)
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(
                    f"Failed to auto-approve join request for user {user_id} in {channel_id}: {e}"
                )

@Client.on_callback_query(filters.regex(r"^fsub_nlink_"))
async def fsub_nlink_cb(client, query):
    await query.answer(
        "⚠️ Invite link is currently unavailable! Please inform the bot admin to give the bot 'Invite Users via Link' permission in the channel.",
        show_alert=True
    )
