import time
import logging
import threading
from functools import wraps
from collections import defaultdict
from config import RATE_LIMIT_MAX, RATE_LIMIT_WINDOW
from bot_instance import bot

logger = logging.getLogger(__name__)
_rate_limit_store = defaultdict(list)
_rate_limit_lock = threading.Lock()

def cek_rate_limit(user_id):
    now = time.time()
    with _rate_limit_lock:
        timestamps = _rate_limit_store[user_id]
        timestamps[:] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        if len(timestamps) >= RATE_LIMIT_MAX:
            sisa = RATE_LIMIT_WINDOW - int(now - timestamps[0]) + 1
            return False, max(sisa, 1)
        timestamps.append(now)
        return True, 0

def rate_limited(func):
    @wraps(func)
    def wrapper(pesan, *args, **kwargs):
        try: user_id = str(pesan.from_user.id)
        except AttributeError: return func(pesan, *args, **kwargs)
        boleh, sisa = cek_rate_limit(user_id)
        if not boleh:
            logger.warning(f"Rate limit kena: user {user_id}")
            try: bot.reply_to(pesan, f"⏳ Sabar bentar bro, lu kena rate limit.\nCoba lagi dalam *{sisa} detik*. 🙏", parse_mode='Markdown')
            except Exception: pass
            return
        return func(pesan, *args, **kwargs)
    return wrapper