# Made by @Awakeners_Bots
# GitHub: https://github.com/Awakener_Bots

from pyrogram import Client, filters
from pyrogram.types import Message
from plugins.settings import fsub

@Client.on_message(filters.command(['fsub', 'forcesub']) & filters.private)
async def fsub_cmd(client: Client, message: Message):
    """Admin command to open Force Sub settings directly."""
    user_id = message.from_user.id
    if user_id not in client.admins and user_id != client.owner:
        return
    
    # Send a message and invoke the unified fsub panel
    msg = await message.reply("<code>Loading Force-Sub Panel...</code>")
    
    # Construct a dummy query object to reuse the rich settings UI
    class DummyQuery:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
        async def answer(self, *args, **kwargs):
            pass

    dummy_query = DummyQuery(msg, message.from_user)
    await fsub(client, dummy_query)
