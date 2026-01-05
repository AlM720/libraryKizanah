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

# إعداد الصفحة لتكون متجاوبة للجوال
st.set_page_config(
    page_title="باحث الكتب",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# --- تصميم CSS متجاوب للجوال أولاً ---
st.markdown("""
<style>
    /* إعدادات أساسية للجوال أولاً */
    * {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 0;
        box-sizing: border-box;
        -webkit-tap-highlight-color: transparent;
    }
    
    html {
        font-size: 16px;
        scroll-behavior: smooth;
    }
    
    body {
        background-color: #ffffff;
        color: #202124;
        min-height: 100vh;
        overflow-x: hidden;
    }
    
    /* شريط الرأس - متجاوب للجوال */
    .header-bar {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid #e8eaed;
        background: white;
        position: sticky;
        top: 0;
        z-index: 1000;
        gap: 10px;
    }
    
    .header-left {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        min-width: 120px;
    }
    
    .header-right {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: flex-end;
    }
    
    /* شعار بسيط بلون واحد */
    .logo {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a73e8;
        text-decoration: none;
        white-space: nowrap;
    }
    
    /* زر المشرف - مصغر للجوال */
    .admin-btn {
        background: none;
        border: 1px solid #dadce0;
        color: #5f6368;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s;
        white-space: nowrap;
    }
    
    .admin-btn:hover {
        background: #f8f9fa;
        border-color: #d2e3fc;
    }
    
    /* عداد الوقت - تصميم مضغوط */
    .session-timer {
        font-size: 0.85rem;
        color: #5f6368;
        background: #f8f9fa;
        padding: 6px 12px;
        border-radius: 20px;
        border: 1px solid #e8eaed;
        text-align: center;
        font-weight: 500;
        white-space: nowrap;
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
    
    /* زر إنهاء الجلسة - ملائم للجوال */
    .end-session-btn {
        background: #ea4335;
        color: white;
        border: none;
        padding: 6px 14px;
        border-radius: 4px;
        font-size: 0.85rem;
        cursor: pointer;
        font-weight: 500;
        transition: background 0.2s;
        white-space: nowrap;
    }
    
    .end-session-btn:hover {
        background: #d32f2f;
    }
    
    /* منطقة البحث الرئيسية - متجاوبة */
    .search-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        padding: 20px 15px;
        width: 100%;
        max-width: 100%;
    }
    
    /* شعار البحث الكبير */
    .search-logo {
        font-size: 2.8rem;
        margin-bottom: 1.5rem;
        font-weight: 400;
        color: #1a73e8;
        text-align: center;
        letter-spacing: -1px;
    }
    
    /* مربع البحث - ملائم للجوال */
    .search-box-container {
        width: 100%;
        max-width: 100%;
        margin: 0 auto 1.5rem;
        position: relative;
    }
    
    .search-box {
        width: 100%;
        padding: 14px 45px 14px 16px;
        font-size: 1rem;
        border: 1px solid #dfe1e5;
        border-radius: 24px;
        outline: none;
        transition: all 0.3s;
        background: white;
        box-shadow: 0 1px 6px rgba(32, 33, 36, 0.08);
        -webkit-appearance: none;
    }
    
    .search-box:hover {
        box-shadow: 0 1px 8px rgba(32, 33, 36, 0.15);
    }
    
    .search-box:focus {
        box-shadow: 0 1px 8px rgba(32, 33, 36, 0.15);
        border-color: #1a73e8;
    }
    
    .search-icon {
        position: absolute;
        right: 16px;
        top: 50%;
        transform: translateY(-50%);
        color: #9aa0a6;
        font-size: 1.2rem;
        pointer-events: none;
    }
    
    /* أزرار البحث - ترتيب عمودي للجوال */
    .search-buttons {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-top: 1.5rem;
        width: 100%;
        max-width: 300px;
    }
    
    @media (min-width: 480px) {
        .search-buttons {
            flex-direction: row;
            justify-content: center;
        }
    }
    
    .search-btn {
        background: #f8f9fa;
        border: 1px solid #f8f9fa;
        color: #3c4043;
        padding: 10px 16px;
        border-radius: 4px;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.2s;
        flex: 1;
        text-align: center;
    }
    
    .search-btn:hover {
        border: 1px solid #dadce0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .search-btn.primary {
        background: #1a73e8;
        color: white;
        border-color: #1a73e8;
    }
    
    .search-btn.primary:hover {
        background: #0d62d9;
        border-color: #0d62d9;
    }
    
    /* نتائج البحث - تصميم للجوال */
    .result-card {
        background: white;
        border: 1px solid #dfe1e5;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        transition: all 0.2s;
        word-break: break-word;
        overflow-wrap: break-word;
    }
    
    .result-card:hover {
        box-shadow: 0 1px 6px rgba(32, 33, 36, 0.12);
        border-color: rgba(223,225,229,0);
    }
    
    .result-title {
        color: #1a0dab;
        font-size: 1.1rem;
        font-weight: 500;
        margin-bottom: 6px;
        text-decoration: none;
        line-height: 1.4;
    }
    
    .result-url {
        color: #006621;
        font-size: 0.85rem;
        margin-bottom: 8px;
        line-height: 1.3;
    }
    
    .result-description {
        color: #4d5156;
        font-size: 0.9rem;
        line-height: 1.5;
        margin-bottom: 12px;
    }
    
    /* أزرار الإجراءات في النتائج */
    .action-buttons {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    
    .action-btn {
        padding: 8px 12px;
        font-size: 0.85rem;
        border-radius: 4px;
        border: 1px solid #dadce0;
        background: white;
        color: #3c4043;
        cursor: pointer;
        flex: 1;
        min-width: 120px;
        text-align: center;
        transition: all 0.2s;
    }
    
    .action-btn:hover {
        background: #f8f9fa;
        border-color: #c6c9ce;
    }
    
    /* تحذيرات النظام */
    .warning-box {
        background: #fff8e1;
        border: 1px solid #fdd663;
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
        color: #5f6368;
        font-size: 0.95rem;
    }
    
    .danger-box {
        background: #fce8e6;
        border: 1px solid #f28b82;
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
        color: #5f6368;
        font-size: 0.95rem;
    }
    
    /* نافذة الدخول */
    .login-modal {
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        padding: 24px 20px;
        width: 100%;
        max-width: 400px;
        margin: 20px auto;
    }
    
    .login-title {
        font-size: 1.5rem;
        color: #202124;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .password-input {
        width: 100%;
        padding: 12px;
        border: 1px solid #dadce0;
        border-radius: 4px;
        font-size: 1rem;
        margin-bottom: 16px;
    }
    
    /* تحسينات للشاشات المتوسطة والكبيرة */
    @media (min-width: 768px) {
        .header-bar {
            padding: 16px 24px;
        }
        
        .logo {
            font-size: 2rem;
        }
        
        .search-logo {
            font-size: 3.5rem;
        }
        
        .search-box-container {
            max-width: 600px;
        }
        
        .search-box {
            padding: 16px 50px 16px 20px;
            font-size: 1.1rem;
        }
        
        .result-title {
            font-size: 1.2rem;
        }
    }
    
    @media (min-width: 1024px) {
        .search-box-container {
            max-width: 700px;
        }
        
        .search-logo {
            font-size: 4rem;
        }
    }
    
    /* إخفاء عناصر streamlit الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        max-width: 100%;
        overflow-x: hidden;
    }
    
    /* تحسين المسافات للجوال */
    .stButton > button {
        width: 100%;
    }
    
    /* تحسين الأعمدة للجوال */
    .stColumn {
        padding: 0 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- ⚙️ إعدادات النظام ---
TIMEOUT_SECONDS = 180
ITEMS_PER_PAGE = 3  # أقل نتائج لكل صفحة للجوال

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
            async for message in client.iter_messages(entity, search=query, limit=50):  # تحديد النتائج للجوال
                if message.file:
                    file_name = message.file.name or message.text[:30] or 'كتاب'
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
    file_name = "كتاب"
    
    # عرض مؤشر التحميل
    progress_text = st.empty()
    progress_bar = st.progress(0)

    async def _download():
        nonlocal file_name
        client = await get_client()
        try:
            entity = await client.get_entity(channel_id)
            message = await client.get_messages(entity, ids=message_id)
            if message and message.file:
                file_name = message.file.name or "كتاب.pdf"
                progress_text.text(f"📥 جاري تحميل: {file_name[:30]}...")
                
                def callback(current, total):
                    if total > 0:
                        progress_bar.progress(current / total)
                
                await client.download_media(message, buffer, progress_callback=callback)
                buffer.seek(0)
            else:
                st.error("الملف غير متوفر")
        except Exception as e:
            st.error(f"فشل في التحميل: {e}")
            return None
        finally:
            await client.disconnect()
            
    loop.run_until_complete(_download())
    loop.close()
    progress_text.empty()
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
        if 'last_query' in st.session_state:
            del st.session_state.last_query
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
    """تنسيق الوقت المتبقي للعرض على الجوال"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes} د {secs} ث"

def format_file_size(size_bytes):
    """تنسيق حجم الملف للعرض على الجوال"""
    if size_bytes < 1024:
        return f"{size_bytes} بايت"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} كيلوبايت"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} ميجابايت"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} جيجابايت"

# ==========================================
# الواجهة الرئيسية - تصميم للجوال أولاً
# ==========================================

# شريط الرأس المتجاوب
header_col1, header_col2, header_col3 = st.columns([2, 3, 2])
with header_col1:
    if not st.session_state.admin_mode and not st.session_state.is_admin:
        if st.button("🔐 دخول المشرف", key="admin_login_btn", use_container_width=True):
            st.session_state.admin_mode = True
            st.rerun()

with header_col3:
    status = check_access()
    if status in ["USER_ACCESS", "ADMIN_ACCESS"]:
        elapsed = time.time() - state.last_activity
        remaining = TIMEOUT_SECONDS - elapsed
        
        # تصميم العداد للجوال
        timer_class = "session-timer"
        if remaining < 60:
            timer_class = "session-timer danger"
        elif remaining < 120:
            timer_class = "session-timer warning"
        
        st.markdown(f'<div class="{timer_class}">⏱️ {format_time(remaining)}</div>', 
                   unsafe_allow_html=True)
        
        if st.button("إنهاء", key="end_session_mobile", use_container_width=True):
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
    # نافذة إدخال كلمة مرور المشرف - مصممة للجوال
    st.markdown('<div class="login-modal">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🔐 دخول المشرف</div>', unsafe_allow_html=True)
    
    password = st.text_input("كلمة المرور:", type="password", key="admin_pass")
    
    login_col1, login_col2 = st.columns(2)
    with login_col1:
        if st.button("دخول", use_container_width=True, type="primary"):
            if password == st.secrets["admin_password"]:
                state.locked = True
                state.current_user_token = st.session_state.user_token
                state.last_activity = time.time()
                st.session_state.is_admin = True
                st.session_state.admin_mode = False
                st.success("✅ تم الدخول كمشرف")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة")
    
    with login_col2:
        if st.button("رجوع", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

elif status is False:
    # النظام مغلق - تصميم للجوال
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 3rem; margin-bottom: 20px;">🔒</div>
        <h2 style="color: #ea4335; margin-bottom: 15px; font-size: 1.5rem;">النظام قيد الاستخدام</h2>
        <p style="color: #5f6368; font-size: 1rem; line-height: 1.6;">
            يرجى الانتظار حتى ينتهي المستخدم الحالي.<br>
            سيتم فتح النظام تلقائياً بعد انتهاء الجلسة.
        </p>
        <div style="margin-top: 30px; font-size: 0.9rem; color: #9aa0a6;">
            ⏱️ الوقت المتبقي: 3 دقائق كحد أقصى
        </div>
    </div>
    """, unsafe_allow_html=True)

elif status == "READY_TO_ENTER":
    # شاشة الدخول - مصممة للجوال
    if 'search_results' not in st.session_state:
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        
        # شعار بسيط بلون واحد
        st.markdown('<div class="search-logo">باحث الكتب</div>', unsafe_allow_html=True)
        
        # مربع البحث
        st.markdown('<div class="search-box-container">', unsafe_allow_html=True)
        query = st.text_input("", 
                             placeholder="ابحث عن كتب، أبحاث، مصادر...",
                             label_visibility="collapsed",
                             key="search_input_mobile")
        st.markdown('<div class="search-icon">🔍</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # أزرار البحث - ترتيب عمودي للجوال
        st.markdown('<div class="search-buttons">', unsafe_allow_html=True)
        
        search_col1, search_col2 = st.columns(2)
        with search_col1:
            if st.button("بحث في المكتبة", key="search_btn_mobile", type="primary", use_container_width=True):
                if query:
                    state.locked = True
                    state.current_user_token = st.session_state.user_token
                    state.last_activity = time.time()
                    with st.spinner("🔍 جاري البحث..."):
                        results = search_books_async(query)
                        st.session_state.search_results = results
                        st.session_state.search_time = time.time()
                        st.session_state.last_query = query
                    st.rerun()
        
        with search_col2:
            if st.button("تفريغ الحقول", key="clear_btn_mobile", use_container_width=True):
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # معلومات إرشادية للجوال
        st.markdown("""
        <div style="text-align: center; margin-top: 30px; color: #5f6368; font-size: 0.9rem; line-height: 1.6;">
            <p>🔍 اكتب كلمات البحث واضغط زر البحث</p>
            <p style="margin-top: 10px;">📚 يمكنك البحث عن كتب PDF، أبحاث، ورسائل علمية</p>
            <p style="margin-top: 15px; font-size: 0.85rem; color: #9aa0a6;">
                ⏱️ مدة الجلسة: 3 دقائق تلقائية<br>
                👆 اضغط على أي كتاب لتنزيله
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

elif status in ["USER_ACCESS", "ADMIN_ACCESS"]:
    # عرض نتائج البحث أو واجهة البحث
    if 'search_results' in st.session_state:
        # شريط البحث في الأعلى للجوال
        search_top_col1, search_top_col2 = st.columns([3, 1])
        with search_top_col1:
            new_query = st.text_input("", 
                                    value=st.session_state.get('last_query', ''),
                                    placeholder="ابحث عن كتب أخرى...",
                                    label_visibility="collapsed",
                                    key="new_search_mobile")
        
        with search_top_col2:
            if st.button("بحث", key="new_search_btn_mobile", use_container_width=True):
                if new_query:
                    with st.spinner("🔍 جاري البحث..."):
                        results = search_books_async(new_query)
                        st.session_state.search_results = results
                        st.session_state.search_time = time.time()
                        st.session_state.last_query = new_query
                        st.session_state.current_page = 0
                    st.rerun()
        
        # عرض عدد النتائج
        results = st.session_state.search_results
        total_results = len(results)
        start_idx = st.session_state.current_page * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, total_results)
        
        st.markdown(f'<div style="color: #70757a; margin: 15px 0; font-size: 0.9rem;">العثور على {total_results} نتيجة</div>', 
                   unsafe_allow_html=True)
        
        if total_results == 0:
            st.info("لم يتم العثور على نتائج. جرب مصطلحات بحث أخرى.")
            if st.button("🔍 بحث جديد", key="new_search_empty", use_container_width=True):
                if 'search_results' in st.session_state:
                    del st.session_state.search_results
                st.session_state.current_page = 0
                st.rerun()
        else:
            # عرض النتائج - تصميم للجوال
            for i in range(start_idx, end_idx):
                if i >= len(results):
                    break
                    
                result = results[i]
                
                # عرض البطاقة
                st.markdown(f'''
                <div class="result-card">
                    <div class="result-title">📚 {result['file_name'][:60]}{'...' if len(result['file_name']) > 60 else ''}</div>
                    <div class="result-url">🆔 المعرف: {result['id']} | 📦 الحجم: {format_file_size(result['size'])}</div>
                    <div class="result-description">
                        {result['caption'][:150] if result['caption'] else "لا يوجد وصف متاح..."}
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                # أزرار الإجراءات
                action_col1, action_col2 = st.columns(2)
                
                with action_col1:
                    if st.button(f"📥 تنزيل", key=f"download_{i}"):
                        with st.spinner("جاري التحميل..."):
                            buffer, filename = download_book_to_memory(result['id'])
                            if buffer:
                                # عرض زر التنزيل
                                st.download_button(
                                    label=f"💾 حفظ الملف",
                                    data=buffer,
                                    file_name=filename,
                                    mime="application/octet-stream",
                                    key=f"save_{i}"
                                )
                
                with action_col2:
                    if st.button(f"ℹ️ تفاصيل", key=f"details_{i}"):
                        with st.expander("تفاصيل الملف"):
                            st.write(f"**الاسم الكامل:** {result['file_name']}")
                            st.write(f"**المعرف:** {result['id']}")
                            st.write(f"**الحجم:** {format_file_size(result['size'])}")
                            st.write(f"**التاريخ:** {result['date'].strftime('%Y-%m-%d %H:%M')}")
                            if result['caption']:
                                st.write(f"**الوصف:** {result['caption']}")
                
                st.markdown("<hr style='margin: 10px 0; border-color: #f1f3f4;'>", unsafe_allow_html=True)
            
            # ترقيم الصفحات للجوال
            if total_results > ITEMS_PER_PAGE:
                total_pages = (total_results + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
                
                # عرض أرقام الصفحات بشكل عمودي للجوال
                pages_to_show = min(3, total_pages)
                for page_num in range(pages_to_show):
                    if st.button(f"صفحة {page_num + 1}", key=f"page_mobile_{page_num}"):
                        st.session_state.current_page = page_num
                        st.rerun()
                
                # إذا كان هناك أكثر من 3 صفحات
                if total_pages > 3:
                    more_pages = st.selectbox("الصفحات الأخرى", 
                                            options=[f"صفحة {i+1}" for i in range(3, total_pages)],
                                            key="more_pages_select")
                    
                    if more_pages:
                        selected_page = int(more_pages.split(" ")[1]) - 1
                        st.session_state.current_page = selected_page
                        st.rerun()
            
            # زر العودة للبحث الرئيسي
            if st.button("🔍 بحث جديد", key="back_to_search_mobile", use_container_width=True):
                if 'search_results' in st.session_state:
                    del st.session_state.search_results
                st.session_state.current_page = 0
                st.rerun()
    
    else:
        # واجهة البحث الرئيسية بعد الدخول
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        
        # شعار
        st.markdown('<div class="search-logo">باحث الكتب</div>', unsafe_allow_html=True)
        
        # مربع البحث
        st.markdown('<div class="search-box-container">', unsafe_allow_html=True)
        query = st.text_input("", 
                            placeholder="ماذا تريد أن تبحث عنه؟",
                            label_visibility="collapsed",
                            key="main_search_mobile")
        st.markdown('<div class="search-icon">🔍</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # أزرار البحث
        search_main_col1, search_main_col2 = st.columns(2)
        with search_main_col1:
            if st.button("🔍 بحث", key="main_search_btn_mobile", type="primary", use_container_width=True):
                if query:
                    with st.spinner("🔍 جاري البحث..."):
                        results = search_books_async(query)
                        st.session_state.search_results = results
                        st.session_state.search_time = time.time()
                        st.session_state.last_query = query
                        st.session_state.current_page = 0
                    st.rerun()
        
        with search_main_col2:
            if st.button("🗑️ مسح", key="main_clear_btn_mobile", use_container_width=True):
                st.rerun()
        
        # معلومات الجلسة
        elapsed = time.time() - state.last_activity
        remaining = TIMEOUT_SECONDS - elapsed
        
        st.markdown(f'''
        <div style="text-align: center; margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 10px; border: 1px solid #e8eaed;">
            <div style="font-size: 0.95rem; color: #5f6368; margin-bottom: 8px;">
                ⏱️ الوقت المتبقي في الجلسة
            </div>
            <div style="font-size: 1.3rem; font-weight: 600; color: #1a73e8;">
                {format_time(remaining)}
            </div>
            <div style="margin-top: 10px; font-size: 0.85rem; color: #9aa0a6;">
                🔍 اكتب واستمتع بالبحث
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # نصائح للبحث على الجوال
        with st.expander("💡 نصائح للبحث"):
            st.markdown("""
            - استخدم كلمات رئيسية محددة
            - جرب أسماء المؤلفين
            - ابحث بالموضوع أو التخصص
            - استخدم اللغة العربية للبحث
            - جرب البحث بالإنجليزية أيضاً
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)

# تذييل الصفحة للجوال
st.markdown("""
<div style="text-align: center; padding: 20px 15px; color: #70757a; font-size: 0.85rem; border-top: 1px solid #e8eaed; margin-top: 30px;">
    <p style="margin-bottom: 8px;">📚 نظام باحث الكتب - المكتبة الرقمية</p>
    <p style="font-size: 0.8rem; color: #9aa0a6;">للاستخدام الأكاديمي والبحث العلمي | متوافق مع الجوال والكمبيوتر</p>
    <div style="margin-top: 15px; font-size: 0.75rem; color: #bdc1c6;">
        ⏱️ جلسة مؤقتة | 🔒 أمان متكامل | 📥 تنزيل مباشر
    </div>
</div>
""", unsafe_allow_html=True)