import os
import asyncio
import json

# Ensure event loop is set for Pyrogram's module-level get_event_loop() calls
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Monkey patch for pyromod Identifier error in Python 3.14
try:
    from pyrogram.types.pyromod.identifier import Identifier

    def safe_get_annotations(cls):
        d = {}
        for c in reversed(cls.__mro__):
            if '__annotations__' in c.__dict__:
                ann = c.__dict__['__annotations__']
                if not isinstance(ann, property):
                    d.update(ann)
        return d

    def _patched_matches(self, update):
        annotations = safe_get_annotations(self.__class__)
        for field in annotations:
            pattern_value = getattr(self, field, None)
            update_value = getattr(update, field, None)
            if pattern_value is not None:
                if isinstance(update_value, list):
                    if isinstance(pattern_value, list):
                        if not set(update_value).intersection(set(pattern_value)): return False
                    elif pattern_value not in update_value: return False
                elif isinstance(pattern_value, list):
                    if update_value not in pattern_value: return False
                elif update_value != pattern_value: return False
        return True

    def _patched_count_populated(self):
        non_null_count = 0
        annotations = safe_get_annotations(self.__class__)
        for attr in annotations:
            if getattr(self, attr, None) is not None:
                non_null_count += 1
        return non_null_count

    Identifier.matches = _patched_matches
    Identifier.count_populated = _patched_count_populated
except Exception:
    pass

from bot import Bot, web_app
from pyrogram import compose

# Static default fallback message templates (can be overridden per setup entry if needed)
default_messages = {
    'START': '<blockquote expandable>__Lorem ipsum dolor sit amet,\nconsectetur adipiscing elit sed.\nVivamus luctus urna sed urna.\nCurabitur blandit tempus porttitor.\nNullam quis risus eget urna.__</blockquote>',
    'FSUB': '',
    'ABOUT': 'ABOUT MSG',
    'REPLY': 'reply_text',
    'START_PHOTO': os.environ.get('START_PIC', ''),
    'FSUB_PHOTO': ''
}

async def main():
    app = []
    
    # Try reading from environment variables first
    api_id_env = os.environ.get("API_ID")
    bot_token_env = os.environ.get("BOT_TOKEN")
    
    if api_id_env and bot_token_env:
        try:
            admins_env = [int(i.strip()) for i in os.environ.get("ADMINS", "").split(",") if i.strip()]
        except Exception:
            admins_env = []
            
        app.append(
            Bot(
                session=os.environ.get("SESSION", "bot"),
                workers=int(os.environ.get("WORKERS", "8")),
                db=int(os.environ.get("DB_CHANNEL", "0")),
                fsub=[], 
                token=os.environ.get("BOT_TOKEN", ""),
                admins=admins_env,
                messages=default_messages,
                auto_del=int(os.environ.get("AUTO_DEL", "300")),
                db_uri=os.environ.get("DATABASE_URI", ""),
                db_name=os.environ.get("DATABASE_NAME", "Cluster0"),
                api_id=int(api_id_env),
                api_hash=os.environ.get("API_HASH", ""),
                protect=os.environ.get("PROTECT", "False").lower() in ("true", "1", "yes"),
                disable_btn=os.environ.get("DISABLE_BTN", "False").lower() in ("true", "1", "yes")
            )
        )
    else:
        # Load setup.json
        with open("setup.json", "r", encoding="utf-8") as f:
            setups = json.load(f)

        # Loop through each bot setup config
        for config in setups:
            session = config["session"]
            workers = config["workers"]
            db = config["db"]
            fsubs = config["fsubs"]
            token = config["token"]
            admins = config["admins"]
            messages = config.get("messages", default_messages)
            auto_del = config["auto_del"]
            db_uri = config["db_uri"]
            db_name = config["db_name"]
            api_id = int(config["api_id"])
            api_hash = config["api_hash"]
            protect = config["protect"]
            disable_btn = config["disable_btn"]

            app.append(
                Bot(
                    session,
                    workers,
                    db,
                    fsubs,
                    token,
                    admins,
                    messages,
                    auto_del,
                    db_uri,
                    db_name,
                    api_id,
                    api_hash,
                    protect,
                    disable_btn
                )
            )

    await compose(app)


async def runner():
    await asyncio.gather(
        main(),
        web_app()
    )

asyncio.run(runner())
