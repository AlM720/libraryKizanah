import streamlit as st
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import nest_asyncio
import io
import time
import uuid
import gc
import re
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
from PIL import Image
from collections import defaultdict

# --- إعدادات الصفحة وتشغيل المهام غير المتزامنة ---
nest_asyncio.apply()

st.set_page_config(
    page_title="المكتبة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تصميم CSS احترافي ومتجاوب ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap');
    
    * { font-family: 'Tajawal', sans-serif; }
    
    /* تحسين العرض على الجوال */
    @media (max-width: 768px) {
        .library-title { font-size: 1.8rem !important; }
        .book-item { padding: 1rem !important; }
        .action-buttons-area { padding: 1rem !important; }
    }

    /* الهيدر */
    .library-header {
        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        padding: 2rem 0;
        margin-bottom: 2rem;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .library-title {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin: 0;
    }
    .library-subtitle {
        color: #ecf0f1;
        text-align: center;
        margin-top: 0.5rem;
    }

    /* بطاقة الكتاب */
    .book-item {
        background: white;
        border: 1px solid #e0e0e0;
        border-right: 5px solid #3498db;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .book-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .book-main-title {
        color: #2c3e50;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .book-details {
        font-size: 0.9rem;
        color: #7f8c8d;
        margin-bottom: 1rem;
    }
    
    /* الأزرار */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    
    /* إخفاء عناصر Streamlit الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- التحقق من الأسرار (Secrets) ---
required_secrets = ["api_id", "api_hash", "session_string", "channel_id"]
# ملاحظة: يمكنك إضافة admin_password و key إذا كنت تستخدم لوحة التحكم
missing_secrets = [key for key in required_secrets if key not in st.secrets]

if missing_secrets:
    st.error(f"⚠️ خطأ: البيانات التالية مفقودة في ملف secrets: {', '.join(missing_secrets)}")
    st.info("تأكد من إضافتها في إعدادات Streamlit Cloud.")
    st.stop()

# --- المتغيرات العامة (State) ---
if 'search_results' not in st.session_state:
    st.session_state.search_results = []

# --- دوال الاتصال بتيليجرام ---
async def get_client():
    try:
        api_id = int(st.secrets["api_id"])
        api_hash = st.secrets["api_hash"]
        session = st.secrets["session_string"]
        client = TelegramClient(StringSession(session), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            st.error("جلسة التيليجرام غير صالحة (Session String).")
            return None
        return client
    except Exception as e:
        st.error(f"خطأ في الاتصال: {e}")
        return None

def search_books_async(query):
    results = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _search():
        client = await get_client()
        if not client: return
        
        try:
            channel_id = int(st.secrets["channel_id"])
            entity = await client.get_entity(channel_id)
            # البحث عن آخر 20 نتيجة مطابقة لتسريع العملية
            async for message in client.iter_messages(entity, search=query, limit=20):
                if message.file:
                    file_name = message.file.name or message.text[:20] or 'ملف بدون اسم'
                    if not file_name.endswith(('.pdf', '.epub', '.rar', '.zip')):
                        file_name += ".pdf"
                    
                    results.append({
                        'id': message.id,
                        'file_name': file_name,
                        'size': message.file.size,
                        'date': message.date,
                        'caption': message.text or ""
                    })
        except Exception as e:
            st.error(f"حدث خطأ أثناء البحث: {e}")
        finally:
            await client.disconnect()

    loop.run_until_complete(_search())
    loop.close()
    return results

def download_book_to_memory(message_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    buffer = io.BytesIO()
    file_name = "downloaded_book"
    
    status_text = st.empty()
    progress_bar = st.progress(0)

    async def _download():
        nonlocal file_name
        client = await get_client()
        if not client: return

        try:
            channel_id = int(st.secrets["channel_id"])
            entity = await client.get_entity(channel_id)
            message = await client.get_messages(entity, ids=message_id)
            
            if message and message.file:
                file_name = message.file.name or "book.pdf"
                status_text.text(f"جاري التحميل: {file_name}...")
                
                def callback(current, total):
                    progress_bar.progress(current / total)
                
                await client.download_media(message, buffer, progress_callback=callback)
                buffer.seek(0)
            else:
                st.error("الملف غير موجود.")
        except Exception as e:
            st.error(f"فشل التحميل: {e}")
        finally:
            await client.disconnect()

    loop.run_until_complete(_download())
    loop.close()
    status_text.empty()
    progress_bar.empty()
    return buffer, file_name

# --- واجهة التطبيق ---

# 1. العنوان
st.markdown("""
<div class="library-header">
    <div class="library-title">المكتبة الرقمية</div>
    <div class="library-subtitle">ابحث وحمل الكتب مباشرة</div>
</div>
""", unsafe_allow_html=True)

# 2. مربع البحث
col_search, col_btn = st.columns([4, 1])
with col_search:
    query = st.text_input("بحث", placeholder="اسم الكتاب أو المؤلف...", label_visibility="collapsed")
with col_btn:
    search_clicked = st.button("بحث 🔍", use_container_width=True, type="primary")

# 3. منطق العرض
if search_clicked and query:
    with st.spinner("جاري البحث في القناة..."):
        st.session_state.search_results = search_books_async(query)

# 4. عرض النتائج
if st.session_state.search_results:
    st.success(f"تم العثور على {len(st.session_state.search_results)} نتيجة")
    
    for item in st.session_state.search_results:
        # حساب الحجم بالميجابايت
        size_mb = item['size'] / (1024 * 1024)
        
        st.markdown(f"""
        <div class="book-item">
            <div class="book-main-title">{item['file_name']}</div>
            <div class="book-details">
                📅 {item['date'].strftime('%Y-%m-%d')} | 📦 {size_mb:.2f} MB
            </div>
            <div style="color: #555; font-size: 0.9rem;">
                {item['caption'][:150]}...
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # أزرار التحميل
        col_dl, col_preview = st.columns([1, 1])
        with col_dl:
             # زر التحميل يحتاج لمعالجة خاصة في ستريم ليت لتفادي إعادة التحميل الكاملة
            if st.button(f"📥 تحضير التحميل", key=f"dl_{item['id']}", use_container_width=True):
                buff, fname = download_book_to_memory(item['id'])
                if buff:
                    st.download_button(
                        label="اضغط هنا للحفظ 💾",
                        data=buff,
                        file_name=fname,
                        mime="application/pdf",
                        key=f"save_{item['id']}",
                        use_container_width=True
                    )

elif search_clicked:
    st.warning("لا توجد نتائج مطابقة.")

# تذييل بسيط
st.markdown("---")
st.markdown("<div style='text-align: center; color: #888;'>مكتبة رقمية تعمل بواسطة Streamlit & Telegram</div>", unsafe_allow_html=True)
