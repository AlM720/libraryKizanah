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

# تفعيل تعدد المهام لبيئة Streamlit
nest_asyncio.apply()

# إعداد الصفحة
st.set_page_config(
    page_title="المكتبة الرقمية - الإدارة",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تصميم CSS الجديد (المتجاوب للجوال) مدمج مع القديم ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap');
    
    * { font-family: 'Tajawal', sans-serif; }
    
    /* تحسين العرض على الجوال */
    @media (max-width: 768px) {
        .library-title { font-size: 1.5rem !important; }
        .book-item { padding: 0.8rem !important; }
        .action-buttons-area { padding: 0.5rem !important; }
        .stButton>button { font-size: 0.9rem !important; padding: 0.5rem !important; }
    }

    /* الهيدر */
    .library-header {
        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        padding: 1.5rem 0;
        margin-bottom: 2rem;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
    }
    .library-title { font-size: 2.2rem; font-weight: 700; margin: 0; }
    .library-subtitle { color: #ecf0f1; margin-top: 0.5rem; font-size: 0.9rem; }

    /* بطاقات الكتب */
    .book-item {
        background: white;
        border: 1px solid #e0e0e0;
        border-right: 4px solid #3498db;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .book-main-title { color: #2c3e50; font-size: 1.2rem; font-weight: 700; }
    .book-metadata { color: #7f8c8d; font-size: 0.85rem; margin: 0.5rem 0; }

    /* شارات الحالة */
    .badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        background: #f1f2f6;
        color: #2f3542;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        border: 1px solid #dfe4ea;
    }
    .badge-admin { background: #ff6b6b; color: white; border: none; }
    .badge-timer { background: #2ed573; color: white; border: none; }

    /* صناديق التنبيهات */
    .waiting-box {
        background: #fff; border: 2px solid #ff9f43; 
        border-radius: 10px; padding: 2rem; text-align: center; margin: 2rem auto;
    }
    .admin-box {
        background: #f8f9fa; border: 1px solid #dee2e6;
        border-radius: 8px; padding: 1rem; margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- ⚙️ إعدادات النظام ---
TIMEOUT_SECONDS = 180
ITEMS_PER_PAGE = 5

# التحقق من الأسرار
required_secrets = ["api_id", "api_hash", "session_string", "channel_id", "admin_password", "key"]
missing = [k for k in required_secrets if k not in st.secrets]
if missing:
    st.error(f"⚠️ البيانات التالية ناقصة في Secrets: {missing}")
    st.stop()

# --- 🧠 الذاكرة المشتركة (State) ---
@st.cache_resource
class GlobalState:
    def __init__(self):
        self.locked = False
        self.current_user_token = None
        self.last_activity = 0

state = GlobalState()

# --- 🆔 تعريف المستخدم والجلسة ---
if 'user_token' not in st.session_state:
    st.session_state.user_token = str(uuid.uuid4())
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False
if 'duplicate_groups' not in st.session_state:
    st.session_state.duplicate_groups = []
if 'scan_completed' not in st.session_state:
    st.session_state.scan_completed = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

def clear_session_data():
    if 'search_results' in st.session_state:
        st.session_state.search_results = []
    gc.collect()

# --- 🔐 منطق الحارس (Queue System) ---
def check_access():
    current_time = time.time()
    
    # المشرف له أولوية
    if st.session_state.admin_mode:
        return "ADMIN_PANEL"
    
    # تحرير القفل إذا انتهى الوقت
    if state.locked and (current_time - state.last_activity > TIMEOUT_SECONDS):
        state.locked = False
        state.current_user_token = None
        clear_session_data()
    
    if st.session_state.is_admin:
        return "ADMIN_ACCESS"

    # المستخدم الحالي النشط
    if state.locked and state.current_user_token == st.session_state.user_token:
        state.last_activity = current_time 
        return "USER_ACCESS"
    
    # النظام متاح
    if not state.locked:
        return "READY_TO_ENTER"
        
    return False

status = check_access()

# --- دوال الاتصال والبحث ---
api_id = int(st.secrets["api_id"])
api_hash = st.secrets["api_hash"]
session_string = st.secrets["session_string"]
channel_id = int(st.secrets["channel_id"])

async def get_client():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.start()
    return client

def search_books_async(query):
    results = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def _search():
        client = await get_client()
        try:
            entity = await client.get_entity(channel_id)
            async for message in client.iter_messages(entity, search=query, limit=20):
                if message.file:
                    file_name = message.file.name or message.text[:20] or 'كتاب'
                    results.append({
                        'id': message.id,
                        'file_name': file_name,
                        'size': message.file.size,
                        'date': message.date,
                        'caption': message.text or ""
                    })
        except Exception as e:
            st.error(f"خطأ: {e}")
        finally:
            await client.disconnect()
    loop.run_until_complete(_search())
    loop.close()
    return results

def download_book_to_memory(message_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    buffer = io.BytesIO()
    file_name = "book.pdf"
    
    # Progress Bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    async def _download():
        nonlocal file_name
        client = await get_client()
        try:
            entity = await client.get_entity(channel_id)
            message = await client.get_messages(entity, ids=message_id)
            if message and message.file:
                file_name = message.file.name or "book.pdf"
                status_text.text(f"جاري التحميل: {file_name}")
                await client.download_media(message, buffer, progress_callback=lambda c,t: progress_bar.progress(c/t))
                buffer.seek(0)
        except Exception as e:
            st.error(f"فشل التحميل: {e}")
            return None
        finally:
            await client.disconnect()
            
    loop.run_until_complete(_download())
    loop.close()
    progress_bar.empty()
    status_text.empty()
    return buffer, file_name

# دوال إدارة المكررات (من الكود الأصلي)
async def scan_for_duplicates():
    client = await get_client()
    files_by_size = defaultdict(list)
    try:
        entity = await client.get_entity(channel_id)
        async for message in client.iter_messages(entity):
            if message.file:
                files_by_size[message.file.size].append({
                    'id': message.id,
                    'name': message.file.name or 'بدون اسم',
                    'size': message.file.size,
                    'date': message.date
                })
        return [files for size, files in files_by_size.items() if len(files) > 1]
    finally:
        await client.disconnect()

async def delete_file(message_id):
    client = await get_client()
    try:
        entity = await client.get_entity(channel_id)
        await client.delete_messages(entity, message_id)
        return True
    except:
        return False
    finally:
        await client.disconnect()

# ==========================================
# 🛑 السيناريو 1: لوحة التحكم (Admin Panel)
# ==========================================
if st.session_state.admin_mode:
    st.markdown('<div class="library-header"><div class="library-title">⚙️ إدارة المكررات</div></div>', unsafe_allow_html=True)
    
    col_exit, col_scan = st.columns([1, 3])
    with col_exit:
        if st.button("🚪 خروج من الإدارة", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()
    
    st.info("🔒 وضع المشرف نشط: النظام مغلق للمستخدمين الآخرين.")
    
    if not st.session_state.scan_completed:
        if st.button("🔍 بدء فحص المكررات الآن", type="primary", use_container_width=True):
            with st.spinner("جاري فحص القناة بالكامل..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                dups = loop.run_until_complete(scan_for_duplicates())
                loop.close()
                st.session_state.duplicate_groups = dups
                st.session_state.scan_completed = True
                st.rerun()
    else:
        # عرض المكررات
        groups = st.session_state.duplicate_groups
        if not groups:
            st.success("✅ القناة نظيفة! لا توجد ملفات مكررة.")
            if st.button("إعادة الفحص"):
                st.session_state.scan_completed = False
                st.rerun()
        else:
            st.warning(f"وجدنا {len(groups)} مجموعة مكررة.")
            
            for i, group in enumerate(groups):
                with st.expander(f"مجموعة #{i+1} - الحجم: {group[0]['size']/(1024*1024):.2f} MB"):
                    for file in group:
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.write(f"📄 {file['name']} ({file['date'].strftime('%Y-%m-%d')})")
                        with c2:
                            if st.button("🗑️ حذف", key=f"del_{file['id']}"):
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                if loop.run_until_complete(delete_file(file['id'])):
                                    st.success("تم الحذف")
                                    time.sleep(1)
                                    st.rerun()
                                loop.close()
    st.stop()

# ==========================================
# 🛑 السيناريو 2: شاشة الانتظار (Locked)
# ==========================================
if status == False:
    st.markdown('<div class="library-header"><div class="library-title">المكتبة الرقمية</div></div>', unsafe_allow_html=True)
    
    time_left = max(0, int(TIMEOUT_SECONDS - (time.time() - state.last_activity)))
    
    st.markdown(f"""
    <div class="waiting-box">
        <h3>⏳ النظام مشغول حالياً</h3>
        <p>يوجد مستخدم آخر يقوم بالبحث والتحميل.</p>
        <h1 style="color:#3498db">{time_left} ثانية</h1>
        <p>سيفتح النظام تلقائياً عند انتهاء العداد.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 تحديث الصفحة", use_container_width=True):
        st.rerun()
        
    with st.expander("🔐 دخول المشرف (للطوارئ)"):
        key = st.text_input("مفتاح المشرف", type="password", key="key_wait")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("إنهاء الجلسة الحالية"):
                if key == st.secrets["key"]:
                    state.locked = False
                    state.current_user_token = None
                    st.success("تم تحرير النظام!")
                    st.rerun()
        with c2:
            if st.button("الدخول للإدارة"):
                if key == st.secrets["key"]:
                    st.session_state.admin_mode = True
                    st.rerun()
    st.stop()

# ==========================================
# 🛑 السيناريو 3: شاشة الترحيب (Welcome)
# ==========================================
elif status == "READY_TO_ENTER":
    st.markdown('<div class="library-header"><div class="library-title">المكتبة الرقمية</div></div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: white; border-radius: 10px;">
        <h3>مرحباً بك 👋</h3>
        <p>المكتبة متاحة الآن للاستخدام.</p>
        <p style="color: grey; font-size: 0.9rem">مدة الجلسة الواحدة 3 دقائق لضمان عدم الضغط على النظام.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 ابدأ الاستخدام الآن", type="primary", use_container_width=True):
        state.locked = True
        state.current_user_token = st.session_state.user_token
        state.last_activity = time.time()
        st.rerun()
        
    # أزرار المشرف المخفية
    st.markdown("---")
    with st.expander("إعدادات المشرف"):
        key = st.text_input("مفتاح المشرف", type="password", key="key_welcome")
        if st.button("دخول لوحة التحكم"):
             if key == st.secrets["key"]:
                st.session_state.admin_mode = True
                st.rerun()
    st.stop()

# ==========================================
# ✅ السيناريو 4: التطبيق الرئيسي (Active)
# ==========================================

# الهيدر والشارات
st.markdown('<div class="library-header"><div class="library-title">المكتبة الرقمية</div></div>', unsafe_allow_html=True)

# شريط المعلومات العلوي
time_left_session = max(0, int(TIMEOUT_SECONDS - (time.time() - state.last_activity)))
col_badge, col_logout = st.columns([2, 1])
with col_badge:
    st.markdown(f'<span class="badge badge-timer">⏱️ متبقي: {time_left_session} ثانية</span>', unsafe_allow_html=True)
with col_logout:
    if st.button("إنهاء الجلسة ❌", use_container_width=True):
        state.locked = False
        state.current_user_token = None
        clear_session_data()
        st.rerun()

# مربع البحث
st.markdown("<br>", unsafe_allow_html=True)
query = st.text_input("بحث", placeholder="ابحث عن كتاب...", label_visibility="collapsed")
if st.button("بحث 🔍", type="primary", use_container_width=True):
    if query:
        state.last_activity = time.time() # تجديد الوقت
        with st.spinner("جاري البحث..."):
            st.session_state.search_results = search_books_async(query)

# عرض النتائج
if 'search_results' in st.session_state and st.session_state.search_results:
    for item in st.session_state.search_results:
        st.markdown(f"""
        <div class="book-item">
            <div class="book-main-title">{item['file_name']}</div>
            <div class="book-metadata">
                📦 {item['size']/(1024*1024):.2f} MB | 📅 {item['date'].strftime('%Y-%m-%d')}
            </div>
            <div style="font-size: 0.9rem; color: #555;">{item['caption'][:100]}...</div>
        </div>
        """, unsafe_allow_html=True)
        
        # أزرار التحميل والمعاينة
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📥 تحضير", key=f"dl_{item['id']}", use_container_width=True):
                state.last_activity = time.time()
                buff, fname = download_book_to_memory(item['id'])
                if buff:
                    st.download_button("حفظ 💾", buff, fname, mime="application/pdf", key=f"s_{item['id']}", use_container_width=True)
