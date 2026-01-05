import streamlit as st
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import nest_asyncio
import io
import time
import uuid
import gc
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
from PIL import Image

# تفعيل تعدد المهام لبيئة Streamlit
nest_asyncio.apply()

# إعداد الصفحة
st.set_page_config(
    page_title="باحث الكتب - المكتبة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تصميم CSS مشابه لجوجل ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    * {
        font-family: 'Roboto', Arial, sans-serif;
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        background-color: #ffffff;
        color: #202124;
    }
    
    /* شريط الرأس - مشابه لجوجل */
    .header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        border-bottom: 1px solid #e8eaed;
        background: white;
        position: sticky;
        top: 0;
        z-index: 1000;
    }
    
    .header-left {
        display: flex;
        align-items: center;
        gap: 24px;
    }
    
    .header-right {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    
    /* زر المشرف */
    .admin-btn {
        background: none;
        border: 1px solid #dadce0;
        color: #5f6368;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .admin-btn:hover {
        background: #f8f9fa;
        border-color: #d2e3fc;
    }
    
    /* عداد الوقت */
    .session-timer {
        font-size: 14px;
        color: #5f6368;
        background: #f8f9fa;
        padding: 8px 16px;
        border-radius: 20px;
        border: 1px solid #e8eaed;
        min-width: 140px;
        text-align: center;
        font-weight: 500;
    }
    
    .session-timer.warning {
        color: #fbbc04;
        background: #fff8e1;
        border-color: #fdd663;
    }
    
    .session-timer.danger {
        color: #ea4335;
        background: #fce8e6;
        border-color: #f28b82;
    }
    
    /* زر إنهاء الجلسة */
    .end-session-btn {
        background: #ea4335;
        color: white;
        border: none;
        padding: 8px 20px;
        border-radius: 4px;
        font-size: 14px;
        cursor: pointer;
        font-weight: 500;
        transition: background 0.2s;
    }
    
    .end-session-btn:hover {
        background: #d32f2f;
    }
    
    /* منطقة البحث الرئيسية */
    .search-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 70vh;
        padding: 40px 20px;
    }
    
    .logo {
        font-size: 92px;
        margin-bottom: 20px;
        font-weight: 400;
        letter-spacing: -4px;
        color: #4285f4;
    }
    
    .logo span:nth-child(1) { color: #4285f4; }
    .logo span:nth-child(2) { color: #ea4335; }
    .logo span:nth-child(3) { color: #fbbc04; }
    .logo span:nth-child(4) { color: #4285f4; }
    .logo span:nth-child(5) { color: #34a853; }
    .logo span:nth-child(6) { color: #ea4335; }
    
    /* مربع البحث */
    .search-box-container {
        width: 100%;
        max-width: 584px;
        margin: 0 auto;
        position: relative;
    }
    
    .search-box {
        width: 100%;
        padding: 15px 50px 15px 20px;
        font-size: 16px;
        border: 1px solid #dfe1e5;
        border-radius: 24px;
        outline: none;
        transition: all 0.3s;
        background: white;
        box-shadow: 0 1px 6px rgba(32, 33, 36, 0.08);
    }
    
    .search-box:hover {
        box-shadow: 0 1px 8px rgba(32, 33, 36, 0.15);
    }
    
    .search-box:focus {
        box-shadow: 0 1px 8px rgba(32, 33, 36, 0.15);
        border-color: #4285f4;
    }
    
    .search-icon {
        position: absolute;
        right: 20px;
        top: 50%;
        transform: translateY(-50%);
        color: #9aa0a6;
        font-size: 20px;
    }
    
    /* أزرار البحث */
    .search-buttons {
        display: flex;
        gap: 12px;
        margin-top: 30px;
        justify-content: center;
    }
    
    .search-btn {
        background: #f8f9fa;
        border: 1px solid #f8f9fa;
        color: #3c4043;
        padding: 10px 20px;
        border-radius: 4px;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s;
        min-width: 140px;
    }
    
    .search-btn:hover {
        border: 1px solid #dadce0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .search-btn.primary {
        background: #4285f4;
        color: white;
        border-color: #4285f4;
    }
    
    .search-btn.primary:hover {
        background: #3367d6;
        border-color: #3367d6;
    }
    
    /* نتائج البحث */
    .result-card {
        background: white;
        border: 1px solid #dfe1e5;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        transition: all 0.2s;
    }
    
    .result-card:hover {
        box-shadow: 0 1px 6px rgba(32, 33, 36, 0.28);
        border-color: rgba(223,225,229,0);
    }
    
    .result-title {
        color: #1a0dab;
        font-size: 20px;
        font-weight: 400;
        margin-bottom: 8px;
        text-decoration: none;
    }
    
    .result-title:hover {
        text-decoration: underline;
    }
    
    .result-url {
        color: #006621;
        font-size: 14px;
        margin-bottom: 10px;
    }
    
    .result-description {
        color: #4d5156;
        font-size: 14px;
        line-height: 1.5;
    }
    
    /* تحذيرات النظام */
    .warning-box {
        background: #fff8e1;
        border: 1px solid #fdd663;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
        color: #5f6368;
    }
    
    .danger-box {
        background: #fce8e6;
        border: 1px solid #f28b82;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
        color: #5f6368;
    }
    
    /* نافذة الدخول */
    .login-modal {
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        padding: 30px;
        max-width: 400px;
        margin: 40px auto;
    }
    
    .login-title {
        font-size: 24px;
        color: #202124;
        margin-bottom: 24px;
        text-align: center;
    }
    
    .password-input {
        width: 100%;
        padding: 12px;
        border: 1px solid #dadce0;
        border-radius: 4px;
        font-size: 16px;
        margin-bottom: 20px;
    }
    
    .password-input:focus {
        border-color: #4285f4;
        outline: none;
        box-shadow: 0 0 0 2px rgba(66,133,244,0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- ⚙️ إعدادات النظام ---
TIMEOUT_SECONDS = 180
ITEMS_PER_PAGE = 5

required_secrets = ["api_id", "api_hash", "session_string", "channel_id", "admin_password", "key"]
if not all(key in st.secrets for key in required_secrets):
    st.error("⚠️ خطأ: تأكد من إعداد ملف secrets.toml بكامل البيانات.")
    st.stop()

# --- 🧠 الذاكرة المشتركة ---
@st.cache_resource
class GlobalState:
    def __init__(self):
        self.locked = False
        self.current_user_token = None
        self.last_activity = 0

state = GlobalState()

# --- 🆔 تعريف المستخدم ---
if 'user_token' not in st.session_state:
    st.session_state.user_token = str(uuid.uuid4())

if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False

if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

# --- دوال الاتصال ---
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
            async for message in client.iter_messages(entity, search=query):
                if message.file:
                    file_name = message.file.name or message.text[:20] or 'كتاب'
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
            st.error(f"خطأ في الاتصال: {e}")
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
    
    col_prog = st.empty()
    progress_bar = st.progress(0)

    async def _download():
        nonlocal file_name
        client = await get_client()
        try:
            entity = await client.get_entity(channel_id)
            message = await client.get_messages(entity, ids=message_id)
            if message and message.file:
                file_name = message.file.name or "book.pdf"
                col_prog.text(f"جاري تحضير الملف: {file_name}")
                
                def callback(current, total):
                    progress_bar.progress(current / total)
                
                await client.download_media(message, buffer, progress_callback=callback)
                buffer.seek(0)
            else:
                st.error("الملف المطلوب غير متوفر")
        except Exception as e:
            st.error(f"فشل في تحميل الملف: {e}")
            return None
        finally:
            await client.disconnect()
            
    loop.run_until_complete(_download())
    loop.close()
    col_prog.empty()
    progress_bar.empty()
    return buffer, file_name

# --- دوال النظام الأمني ---
def check_access():
    current_time = time.time()
    
    if st.session_state.admin_mode:
        return "ADMIN_PANEL"
    
    if state.locked and (current_time - state.last_activity > TIMEOUT_SECONDS):
        state.locked = False
        state.current_user_token = None
        if 'search_results' in st.session_state:
            del st.session_state.search_results
        if 'search_time' in st.session_state:
            del st.session_state.search_time
        gc.collect()
    
    if st.session_state.is_admin:
        return "ADMIN_ACCESS"

    if state.locked and state.current_user_token == st.session_state.user_token:
        state.last_activity = current_time 
        return "USER_ACCESS"
    
    if not state.locked:
        return "READY_TO_ENTER"
        
    return False

def format_time(seconds):
    """تنسيق الوقت المتبقي"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

# ==========================================
# الواجهة الرئيسية
# ==========================================

# شريط الرأس
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if not st.session_state.admin_mode and not st.session_state.is_admin:
        if st.button("🔐 دخول المشرف", key="admin_login_btn"):
            st.session_state.admin_mode = True
            st.rerun()

with col3:
    status = check_access()
    if status in ["USER_ACCESS", "ADMIN_ACCESS"]:
        elapsed = time.time() - state.last_activity
        remaining = TIMEOUT_SECONDS - elapsed
        
        # تحديد لون العداد بناءً على الوقت المتبقي
        timer_class = "session-timer"
        if remaining < 60:
            timer_class = "session-timer danger"
        elif remaining < 120:
            timer_class = "session-timer warning"
        
        st.markdown(f'<div class="{timer_class}">⏳ {format_time(remaining)}</div>', 
                   unsafe_allow_html=True)
        
        if st.button("إنهاء الجلسة", key="end_session"):
            state.locked = False
            state.current_user_token = None
            st.session_state.user_token = str(uuid.uuid4())
            st.session_state.is_admin = False
            if 'search_results' in st.session_state:
                del st.session_state.search_results
            gc.collect()
            st.rerun()

# عرض حالة النظام
status = check_access()

if status == "ADMIN_PANEL":
    # نافذة إدخال كلمة مرور المشرف
    st.markdown('<div class="login-modal">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🔐 دخول المشرف</div>', unsafe_allow_html=True)
    
    password = st.text_input("كلمة المرور:", type="password", key="admin_pass")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("دخول", use_container_width=True):
            if password == st.secrets["admin_password"]:
                state.locked = True
                state.current_user_token = st.session_state.user_token
                state.last_activity = time.time()
                st.session_state.is_admin = True
                st.session_state.admin_mode = False
                st.success("✅ تم الدخول كمشرف بنجاح!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة")
        
        if st.button("رجوع", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

elif status is False:
    # النظام مغلق - ينتظر شخص آخر
    st.markdown("""
    <div style="text-align: center; padding: 100px 20px;">
        <h2 style="color: #ea4335; margin-bottom: 20px;">🔒 النظام قيد الاستخدام</h2>
        <p style="color: #5f6368; font-size: 16px; max-width: 500px; margin: 0 auto;">
            يرجى الانتظار حتى ينتهي المستخدم الحالي من استخدام النظام.<br>
            سيتم فتح النظام تلقائياً بعد انتهاء الجلسة الحالية.
        </p>
    </div>
    """, unsafe_allow_html=True)

elif status == "READY_TO_ENTER":
    # شاشة الدخول - واجهة جوجل
    if 'search_results' not in st.session_state:
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        
        # الشعار الملون
        st.markdown('''
        <div class="logo">
            <span>ب</span><span>ح</span><span>ث</span><span>ك</span><span>ت</span><span>ب</span>
        </div>
        ''', unsafe_allow_html=True)
        
        # مربع البحث
        st.markdown('<div class="search-box-container">', unsafe_allow_html=True)
        query = st.text_input("", placeholder="ابحث عن الكتب والمصادر...", 
                            label_visibility="collapsed",
                            key="search_input")
        st.markdown('<div class="search-icon">🔍</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # أزرار البحث
        st.markdown('<div class="search-buttons">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("بحث في المكتبة", key="search_btn", use_container_width=True):
                if query:
                    state.locked = True
                    state.current_user_token = st.session_state.user_token
                    state.last_activity = time.time()
                    with st.spinner("🔍 جاري البحث..."):
                        results = search_books_async(query)
                        st.session_state.search_results = results
                        st.session_state.search_time = time.time()
                    st.rerun()
        with col2:
            if st.button("تفريغ الحقول", key="clear_btn", use_container_width=True):
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # معلومات النظام
        st.markdown("""
        <div style="text-align: center; margin-top: 50px; color: #5f6368; font-size: 14px;">
            <p>أدخل كلمات البحث واضغط على زر البحث للبدء</p>
            <p style="margin-top: 10px;">⏱️ مدة الجلسة: 3 دقائق تلقائية</p>
        </div>
        """, unsafe_allow_html=True)

elif status in ["USER_ACCESS", "ADMIN_ACCESS"]:
    # عرض نتائج البحث أو واجهة البحث
    if 'search_results' in st.session_state:
        # شريط البحث في الأعلى
        col_search1, col_search2 = st.columns([6, 1])
        with col_search1:
            new_query = st.text_input("", 
                                    value=st.session_state.get('last_query', ''),
                                    placeholder="ابحث عن كتب أخرى...",
                                    label_visibility="collapsed",
                                    key="new_search")
        
        with col_search2:
            if st.button("بحث جديد", use_container_width=True):
                if new_query:
                    with st.spinner("🔍 جاري البحث..."):
                        results = search_books_async(new_query)
                        st.session_state.search_results = results
                        st.session_state.search_time = time.time()
                        st.session_state.last_query = new_query
                    st.rerun()
        
        # عرض عدد النتائج
        results = st.session_state.search_results
        total_results = len(results)
        start_idx = st.session_state.current_page * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, total_results)
        
        st.markdown(f'<div style="color: #70757a; margin: 20px 0;">عرض النتائج {start_idx + 1}-{end_idx} من {total_results}</div>', 
                   unsafe_allow_html=True)
        
        # عرض النتائج
        for i in range(start_idx, end_idx):
            if i >= len(results):
                break
                
            result = results[i]
            with st.container():
                st.markdown(f'''
                <div class="result-card">
                    <div class="result-title">📚 {result['file_name']}</div>
                    <div class="result-url">المعرف: {result['id']} | الحجم: {result['size']:,} بايت</div>
                    <div class="result-description">
                        {result['caption'][:200] if result['caption'] else "لا يوجد وصف متاح"}
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                # أزرار التنزيل والمعاينة
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                with col_btn1:
                    if st.button(f"📥 تنزيل", key=f"download_{i}"):
                        with st.spinner("جاري التحميل..."):
                            buffer, filename = download_book_to_memory(result['id'])
                            if buffer:
                                st.download_button(
                                    label=f"💾 حفظ {filename}",
                                    data=buffer,
                                    file_name=filename,
                                    mime="application/octet-stream",
                                    key=f"save_{i}"
                                )
                
                with col_btn2:
                    if st.button(f"👁️ معاينة", key=f"preview_{i}"):
                        with st.spinner("جاري تحضير المعاينة..."):
                            # هنا يمكن إضافة معاينة الصفحة الأولى
                            st.info("خاصية المعاينة قيد التطوير")
                
                st.markdown("---")
        
        # ترقيم الصفحات
        if total_results > ITEMS_PER_PAGE:
            total_pages = (total_results + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            pagination_cols = st.columns([1] * min(5, total_pages) + [2])
            
            for idx, col in enumerate(pagination_cols[:-1]):
                if idx < total_pages:
                    page_num = idx + 1
                    if col.button(str(page_num), key=f"page_{idx}"):
                        st.session_state.current_page = idx
                        st.rerun()
        
        # زر العودة للبحث
        if st.button("🔍 بحث جديد", use_container_width=True):
            if 'search_results' in st.session_state:
                del st.session_state.search_results
            st.session_state.current_page = 0
            st.rerun()
    
    else:
        # واجهة البحث الرئيسية (بعد الدخول)
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        
        # الشعار الملون
        st.markdown('''
        <div class="logo">
            <span>ب</span><span>ح</span><span>ث</span><span>ك</span><span>ت</span><span>ب</span>
        </div>
        ''', unsafe_allow_html=True)
        
        # مربع البحث
        st.markdown('<div class="search-box-container">', unsafe_allow_html=True)
        query = st.text_input("", placeholder="ابدأ البحث عن الكتب...", 
                            label_visibility="collapsed",
                            key="main_search")
        st.markdown('<div class="search-icon">🔍</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # أزرار البحث
        st.markdown('<div class="search-buttons">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("بحث في المكتبة", key="main_search_btn", use_container_width=True):
                if query:
                    with st.spinner("🔍 جاري البحث..."):
                        results = search_books_async(query)
                        st.session_state.search_results = results
                        st.session_state.search_time = time.time()
                        st.session_state.last_query = query
                    st.rerun()
        with col2:
            if st.button("تفريغ الحقول", key="main_clear_btn", use_container_width=True):
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # معلومات الجلسة
        elapsed = time.time() - state.last_activity
        remaining = TIMEOUT_SECONDS - elapsed
        
        st.markdown(f'''
        <div style="text-align: center; margin-top: 40px; color: #5f6368; font-size: 14px;">
            <p>⏱️ الوقت المتبقي: <strong>{format_time(remaining)}</strong></p>
            <p style="margin-top: 10px;">🔍 ابحث عن كتب، دراسات، أبحاث، وملفات PDF</p>
        </div>
        ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# تذييل الصفحة
st.markdown("""
<div style="text-align: center; padding: 30px; color: #70757a; font-size: 14px; border-top: 1px solid #e8eaed; margin-top: 40px;">
    <p>نظام باحث الكتب - المكتبة الرقمية | © 2024</p>
    <p style="margin-top: 10px;">للاستخدام الأكاديمي والبحث العلمي</p>
</div>
""", unsafe_allow_html=True)