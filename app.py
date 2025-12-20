# app.py  (Streamlit + Telethon + نتيجة واحدة + بحث داخل أي جزء من النص)
import streamlit as st
from telethon.sync import TelegramClient
from telethon.tl.types import InputMessagesFilterDocument
import asyncio
import unicodedata

# ---------- الأسرار (من إعدادات Streamlit) ----------
api_id   = int(st.secrets["api_id"])
api_hash = st.secrets["api_hash"]
bot_token = st.secrets["bot_token"]
channel_id = int(st.secrets["channel_id"])

# ---------- تطبيع النص ----------
def normalize_arabic(text: str) -> str:
    if not text: return ""
    text = unicodedata.normalize("NFKC", text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    hamza = "ء"
    for k, v in {"أ":"ا", "إ":"ا", "ئ":hamza, "ؤ":hamza, "ء":hamza}.items():
        text = text.replace(k, v)
    return text.replace("ى", "ي").strip()

# ---------- جلب النتائج ----------
async def fetch_books(keyword: str, limit: int = 20):
    client = TelegramClient("bot_session", api_id, api_hash",
                            connection_retries=2, request_retries=2, timeout=10)
    await client.start(bot_token=bot_token)
    keyword_norm = normalize_arabic(keyword)
    results = []
    async for msg in client.iter_messages(
        channel_id,
        filter=InputMessagesFilterDocument(),
        limit=limit
    ):
        if msg.document:
            msg_text_norm = normalize_arabic(msg.message or "")
            file_name = msg.document.attributes[0].file_name if msg.document.attributes else ""
            file_text_norm = normalize_arabic(file_name)

            if keyword_norm in msg_text_norm or keyword_norm in file_text_norm:
                results.append({
                    "title": msg.message or "بدون عنوان",
                    "file_name": file_name or "unknown",
                    "size": msg.document.size,
                    "date": msg.date
                })
    await client.disconnect()
    return results

# ---------- واجهة Streamlit ----------
st.set_page_config(page_title="محرّك كتبي", layout="centered")
st.title("🔍 محرّك كتبي")
st.markdown("ابحث في مكتبتك التلغرافية دون القلق من الهمزات أو التشكيل.")

keyword = st.text_input("اكتب اسم الكتاب أو كلمة مفتاحية:")
if st.button("بحث"):
    if not keyword.strip():
        st.warning("أدخل كلمة للبحث!")
    else:
        with st.spinner("جاري البحث..."):
            try:
                hits = asyncio.run(fetch_books(keyword))
            except Exception as e:
                st.error(f"⚠️ تعذر الاتصال بـ Telegram حالياً.\nالخطأ:\n{e}")
                st.stop()

        if not hits:
            st.info("لم يُعثر على نتائج.")
        else:
            st.success(f"تم العثور على {len(hits)} نتيجة")
            for h in hits:
                sz_mb = h["size"] / 1024 / 1024
                date_str = h["date"].strftime("%Y-%m-%d")
                with st.expander(f"{h['title']}  –  {sz_mb:.2f} ميجا"):
                    st.write(f"**الملف:** {h['file_name']}")
                    st.write(f"**التاريخ:** {date_str}")
