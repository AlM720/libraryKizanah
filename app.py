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
    page_title="المكتبة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تصميم CSS احترافي بخلفية بيضاء ومضيئة ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Tajawal:wght@300;400;500;700&display=swap');
    
    * {
        font-family: 'Tajawal', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Amiri', serif;
    }

    /* الخلفية البيضاء المضيئة */
    .stApp {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        color: #2c3e50;
    }

    /* الهيدر الرئيسي */
    .main-header {
        background: linear-gradient(135deg, #ffffff 0%, #e8f4f8 100%);
        backdrop-filter: blur(10px);
        padding: 3rem 0;
        margin-bottom: 3rem;
        border-bottom: 1px solid rgba(44, 62, 80, 0.1);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }

    /* عنوان المكتبة */
    .library-title {
        color: #2c3e50;
        font-size: 3.5rem;
        font-weight: 700;
        text-align: center;
        margin: 0;
        letter-spacing: 1px;
        background: linear-gradient(45deg, #2c3e50, #3498db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* الشعار الفرعي */
    .library-subtitle {
        color: #7f8c8d;
        text-align: center;
        font-size: 1.3rem;
        margin-top: 1rem;
        font-weight: 300;
    }

    /* حاوية البحث المركزية */
    .search-container {
        max-width: 800px;
        margin: 0 auto 2rem auto;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 25px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(44, 62, 80, 0.1);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
    }

    /* حقل البحث */
    .stTextInput>div>div>input {
        background: #ffffff !important;
        border: 2px solid #e0e0e0 !important;
        border-radius: 50px !important;
        padding: 1.5rem 2rem !important;
        font-size: 1.3rem !important;
        color: #2c3e50 !important;
        font-weight: 400 !important;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
    }

    .stTextInput>div>div>input:focus {
        border-color: #3498db !important;
        background: #ffffff !important;
        box-shadow: 0 0 30px rgba(52, 152, 219, 0.3) !important;
        color: #2c3e50 !important;
    }

    .stTextInput>div>div>input::placeholder {
        color: #95a5a6 !important;
    }

    /* زر البحث */
    .stButton>button {
        background: linear-gradient(45deg, #3498db, #2980b9) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 1rem 3rem !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease;
        margin-top: 1rem;
        box-shadow: 0 5px 20px rgba(52, 152, 219, 0.3);
    }

    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 40px rgba(52, 152, 219, 0.4);
        background: linear-gradient(45deg, #2980b9, #3498db) !important;
    }

    /* شريط المؤقت العلوي */
    .timer-bar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        padding: 0.5rem;
        z-index: 1000;
        border-bottom: 1px solid rgba(44, 62, 80, 0.1);
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }

    .timer-text {
        color: #2c3e50;
        text-align: center;
        font-size: 0.9rem;
        font-weight: 400;
    }

    /* زر دخول المشرف */
    .admin-button {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid rgba(44, 62, 80, 0.2) !important;
        border-radius: 50% !important;
        width: 60px !important;
        height: 60px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(10px);
        box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
    }

    .admin-button:hover {
        background: rgba(52, 152, 219, 0.9) !important;
        transform: scale(1.1);
        box-shadow: 0 10px 30px rgba(52, 152, 219, 0.3);
    }

    /* نتائج البحث */
    .search-results {
        max-width: 1000px;
        margin: 2rem auto;
    }

    .book-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(44, 62, 80, 0.1);
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
    }

    .book-card:hover {
        background: #ffffff;
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }

    /* رسائل الحالة */
    .stSuccess, .stError, .stWarning, .stInfo {
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid rgba(44, 62, 80, 0.1) !important;
        border-radius: 10px !important;
        color: #2c3e50 !important;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
    }

    /* إخفاء العناصر الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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

if 'search_results' not in st.session_state:
    st.session_state.search_results = []

if 'search_time' not in st.session_state:
    st.session_state.search_time = None

# --- دالة تنظيف الذاكرة ---
def clear_session_data():
    if 'search_results' in st.session_state:
        st.session_state.search_results = []
    if 'search_time' in st.session_state:
        st.session_state.search_time = None
    gc.collect()

# --- 🔐 منطق الحارس ---
def check_access():
    current_time = time.time()
    
    if st.session_state.admin_mode:
        return "ADMIN_PANEL"
    
    if state.locked and (current_time - state.last_activity > TIMEOUT_SECONDS):
        state.locked = False
        state.current_user_token = None
        clear_session_data()
    
    if st.session_state.is_admin:
        return "ADMIN_ACCESS"

    if state.locked and state.current_user_token == st.session_state.user_token:
        state.last_activity = current_time 
        return "USER_ACCESS"
    
    if not state.locked:
        return "READY_TO_ENTER"
        
    return False

status = check_access()

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

def get_pdf_page_count(message_id):
    try:
        buffer, file_name = download_book_to_memory(message_id)
        if buffer and file_name.lower().endswith('.pdf'):
            pdf_reader = PdfReader(buffer)
            page_count = len(pdf_reader.pages)
            buffer.close()
            gc.collect()
            return page_count
        else:
            return None
    except Exception as e:
        st.error(f"خطأ في حساب الصفحات: {e}")
        return None

def get_first_page_preview(message_id):
    try:
        buffer, file_name = download_book_to_memory(message_id)
        if buffer and file_name.lower().endswith('.pdf'):
            pdf_document = fitz.open(stream=buffer.read(), filetype="pdf")
            
            if len(pdf_document) > 0:
                first_page = pdf_document[0]
                zoom = 2
                mat = fitz.Matrix(zoom, zoom)
                pix = first_page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                pdf_document.close()
                buffer.close()
                gc.collect()
                
                return img
            else:
                pdf_document.close()
                buffer.close()
                return None
        else:
            return None
    except Exception as e:
        st.error(f"خطأ في إنشاء المعاينة: {e}")
        return None

# ==========================================
# الواجهة الرئيسية
# ==========================================

# شريط المؤقت العلوي
if status == "USER_ACCESS":
    st.markdown("""
    <div class="timer-bar">
        <div class="timer-text">
            ⏰ الجلسة نشطة | الوقت المتبقي: {} ثانية
        </div>
    </div>
    """.format(int(TIMEOUT_SECONDS - (time.time() - state.last_activity))), unsafe_allow_html=True)

# الهيدر الرئيسي
st.markdown("""
<div class="main-header">
    <h1 class="library-title">المكتبة الرقمية</h1>
    <p class="library-subtitle">اكتشف عالم المعرفة بين يديك</p>
</div>
""", unsafe_allow_html=True)

# حاوية البحث المركزية
st.markdown('<div class="search-container">', unsafe_allow_html=True)

# حقل البحث
search_query = st.text_input(
    "",
    placeholder="ابحث عن كتاب...",
    label_visibility="collapsed"
)

# زر البحث
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔍 بحث", use_container_width=True):
        if search_query:
            with st.spinner("جاري البحث..."):
                results = search_books_async(search_query)
                st.session_state.search_results = results
                st.session_state.search_time = time.time()
                st.session_state.current_page = 0
        else:
            st.warning("يرجى إدخال كلمة بحث")

st.markdown('</div>', unsafe_allow_html=True)

# عرض النتائج
if st.session_state.search_results:
    st.markdown('<div class="search-results">', unsafe_allow_html=True)
    
    results = st.session_state.search_results
    total_pages = (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    # عرض النتائج الحالية
    start_idx = st.session_state.current_page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(results))
    
    for result in results[start_idx:end_idx]:
        with st.container():
            st.markdown(f"""
            <div class="book-card">
                <h3 style="color: #2c3e50; margin-bottom: 0.5rem;">📚 {result['file_name']}</h3>
                <p style="color: #7f8c8d; font-size: 0.9rem; margin-bottom: 0.5rem;">
                    📅 {result['date'].strftime('%Y-%m-%d')} | 📊 {result['size'] / 1024 / 1024:.1f} ميجابايت
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("⬇️ تحميل", key=f"download_{result['id']}"):
                    buffer, file_name = download_book_to_memory(result['id'])
                    if buffer:
                        st.download_button(
                            label="💾 حفظ الملف",
                            data=buffer,
                            file_name=file_name,
                            mime="application/octet-stream",
                            key=f"save_{result['id']}"
                        )
            
            with col2:
                if st.button("👁️ معاينة", key=f"preview_{result['id']}"):
                    preview = get_first_page_preview(result['id'])
                    if preview:
                        st.image(preview, caption="الصفحة الأولى", use_column_width=True)
                    else:
                        st.error("لا توجد معاينة متاحة")
            
            with col3:
                if st.button("📄 عدد الصفحات", key=f"pages_{result['id']}"):
                    pages = get_pdf_page_count(result['id'])
                    if pages:
                        st.info(f"📖 عدد الصفحات: {pages}")
                    else:
                        st.error("لا يمكن حساب عدد الصفحات")
    
    # التنقل بين الصفحات
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            prev, page_info, next_btn = st.columns([1, 2, 1])
            with prev:
                if st.session_state.current_page > 0:
                    if st.button("⬅️ السابق"):
                        st.session_state.current_page -= 1
                        st.rerun()
            
            with page_info:
                st.write(f"الصفحة {st.session_state.current_page + 1} من {total_pages}")
            
            with next_btn:
                if st.session_state.current_page < total_pages - 1:
                    if st.button("التالي ➡️"):
                        st.session_state.current_page += 1
                        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# زر دخول المشرف
if st.button("⚙️", key="admin_button", help="دخول المشرف"):
    st.session_state.show_admin_login = True

# نافذة تسجيل دخول المشرف
if 'show_admin_login' in st.session_state and st.session_state.show_admin_login:
    with st.container():
        st.markdown("""
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
                    background: rgba(255, 255, 255, 0.9); z-index: 2000; 
                    display: flex; align-items: center; justify-content: center;">
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="background: #ffffff; padding: 2rem; 
                        border-radius: 15px; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1); 
                        border: 1px solid rgba(44, 62, 80, 0.1);">
            """, unsafe_allow_html=True)
            
            st.markdown("<h3 style='text-align: center; color: #2c3e50;'>🔐 دخول المشرف</h3>", unsafe_allow_html=True)
            
            admin_password = st.text_input("كلمة المرور", type="password", key="admin_pass")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("دخول"):
                    if admin_password == st.secrets["admin_password"]:
                        st.session_state.is_admin = True
                        st.session_state.admin_mode = True
                        st.session_state.show_admin_login = False
                        st.rerun()
                    else:
                        st.error("كلمة مرور خاطئة")
            
            with col2:
                if st.button("إلغاء"):
                    st.session_state.show_admin_login = False
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# نافذة دخول المستخدم
if status == "READY_TO_ENTER":
    with st.container():
        st.markdown("""
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
                    background: rgba(255, 255, 255, 0.95); z-index: 3000; 
                    display: flex; align-items: center; justify-content: center;">
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="background: #ffffff; padding: 3rem; 
                        border-radius: 20px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1); 
                        border: 1px solid rgba(44, 62, 80, 0.1); text-align: center;">
            """, unsafe_allow_html=True)
            
            st.markdown("<h2 style='color: #2c3e50; margin-bottom: 2rem;'>🚪 الدخول إلى المكتبة</h2>", unsafe_allow_html=True)
            
            if st.button("دخول", use_container_width=True, type="primary"):
                state.locked = True
                state.current_user_token = st.session_state.user_token
                state.last_activity = time.time()
                st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
