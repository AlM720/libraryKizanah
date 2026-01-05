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

# تفعيل تعدد المهام لبيئة Streamlit
nest_asyncio.apply()

# إعداد الصفحة
st.set_page_config(
    page_title="باحث الكتب - المكتبة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تصميم CSS احترافي شبيه بجوجل وتطبيق تراث ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Tajawal:wght@300;400;500;700&display=swap');
    
    * {
        font-family: 'Tajawal', sans-serif;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
    }
    
    /* إخفاء عناصر streamlit الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* تصميم الصفحة الرئيسية */
    .main-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 70vh;
        padding: 2rem;
    }
    
    .logo-container {
        text-align: center;
        margin-bottom: 2rem;
        animation: fadeInDown 0.8s ease-out;
    }
    
    .main-logo {
        font-size: 5rem;
        margin-bottom: 1rem;
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));
    }
    
    .main-title {
        font-family: 'Amiri', serif;
        font-size: 3rem;
        font-weight: 700;
        color: #2c3e50;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .main-subtitle {
        font-size: 1.2rem;
        color: #7f8c8d;
        margin-top: 0.5rem;
    }
    
    /* صندوق البحث الرئيسي */
    .search-container {
        width: 100%;
        max-width: 650px;
        margin: 2rem auto;
        animation: fadeInUp 0.8s ease-out;
    }
    
    .stTextInput > div > div > input {
        border: 2px solid #e0e0e0 !important;
        border-radius: 50px !important;
        padding: 1.2rem 2rem !important;
        font-size: 1.1rem !important;
        background: white !important;
        color: #2c3e50 !important;
        font-weight: 500 !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3498db !important;
        box-shadow: 0 4px 20px rgba(52, 152, 219, 0.3) !important;
        outline: none !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #95a5a6 !important;
        font-weight: 400 !important;
    }
    
    /* أزرار البحث */
    .search-buttons {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin-top: 1.5rem;
    }
    
    .stButton > button {
        background: white !important;
        color: #5f6368 !important;
        border: 1px solid #f0f0f0 !important;
        border-radius: 4px !important;
        padding: 0.7rem 1.5rem !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }
    
    .stButton > button:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
        border-color: #dadce0 !important;
        transform: translateY(-1px);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* أزرار التحكم في الأعلى */
    .control-buttons {
        position: fixed;
        top: 1rem;
        left: 1rem;
        display: flex;
        gap: 0.5rem;
        z-index: 1000;
        flex-direction: column;
    }
    
    .control-btn {
        background: white !important;
        color: #5f6368 !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.85rem !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        min-width: 120px;
    }
    
    .control-btn:hover {
        box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
        background: #f8f9fa !important;
    }
    
    /* عداد الجلسة */
    .session-timer {
        position: fixed;
        top: 1rem;
        right: 1rem;
        background: white;
        padding: 0.8rem 1.2rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        font-weight: 500;
        color: #2c3e50;
        z-index: 1000;
        min-width: 150px;
        text-align: center;
    }
    
    .timer-warning {
        background: #fff3cd !important;
        border: 1px solid #ffc107;
    }
    
    .timer-danger {
        background: #f8d7da !important;
        border: 1px solid #dc3545;
        animation: pulse 1s infinite;
    }
    
    /* نتائج البحث */
    .result-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        border: 1px solid #f0f0f0;
    }
    
    .result-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }
    
    .result-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1a73e8;
        margin-bottom: 0.5rem;
        font-family: 'Amiri', serif;
    }
    
    .result-meta {
        color: #5f6368;
        font-size: 0.9rem;
        margin: 0.3rem 0;
    }
    
    .result-description {
        color: #3c4043;
        line-height: 1.6;
        margin-top: 0.8rem;
    }
    
    /* رسائل التنبيه */
    .alert-box {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 2rem auto;
        max-width: 600px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        text-align: center;
        border: 2px solid #e8f4fd;
    }
    
    .alert-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    /* الرسوم المتحركة */
    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.02);
        }
    }
    
    /* تصميم متجاوب للجوال */
    @media (max-width: 768px) {
        .main-logo {
            font-size: 3.5rem;
        }
        
        .main-title {
            font-size: 2rem;
        }
        
        .main-subtitle {
            font-size: 1rem;
        }
        
        .search-container {
            max-width: 90%;
        }
        
        .control-buttons {
            position: static;
            flex-direction: row;
            justify-content: center;
            margin: 1rem 0;
        }
        
        .session-timer {
            position: static;
            margin: 1rem auto;
            width: fit-content;
        }
        
        .stTextInput > div > div > input {
            padding: 1rem 1.5rem !important;
            font-size: 1rem !important;
        }
    }
    
    /* صفحات النتائج */
    .results-header {
        background: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .results-count {
        color: #70757a;
        font-size: 0.95rem;
    }
    
    /* أزرار التحميل */
    .download-btn {
        background: #1a73e8 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.7rem 1.5rem !important;
        font-weight: 500 !important;
    }
    
    .download-btn:hover {
        background: #1557b0 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- ⚙️ إعدادات النظام ---
TIMEOUT_SECONDS = 180
ITEMS_PER_PAGE = 5

required_secrets = ["api_id", "api_hash", "session_string", "channel_id", "admin_password"]
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

if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

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

def clean_description(text):
    """إزالة الروابط من النص"""
    if not text:
        return "لا يوجد وصف متاح لهذا الكتاب."
    
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r't\.me/\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text if text else "لا يوجد وصف متاح لهذا الكتاب."

def format_file_size(size_bytes):
    """تحويل حجم الملف إلى صيغة قابلة للقراءة"""
    for unit in ['بايت', 'كيلوبايت', 'ميجابايت', 'جيجابايت']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} تيرابايت"

# ==========================================
# الواجهة الرئيسية
# ==========================================

status = check_access()

# عرض أزرار التحكم في الأعلى (للجوال في الوسط)
col_control = st.container()
with col_control:
    if status in ["USER_ACCESS", "ADMIN_ACCESS"]:
        # للشاشات الكبيرة: في اليسار
        # للجوال: في الوسط
        cols = st.columns([1, 1, 1])
        
        with cols[0]:
            if st.button("🚪 إنهاء الجلسة", key="end_session", help="إنهاء جلسة البحث الحالية"):
                state.locked = False
                state.current_user_token = None
                st.session_state.is_admin = False
                clear_session_data()
                st.rerun()
        
        with cols[1]:
            # عرض عداد الوقت
            if state.locked:
                remaining = TIMEOUT_SECONDS - int(time.time() - state.last_activity)
                minutes = remaining // 60
                seconds = remaining % 60
                
                if remaining < 30:
                    timer_class = "timer-danger"
                    timer_icon = "⚠️"
                elif remaining < 60:
                    timer_class = "timer-warning"
                    timer_icon = "⏰"
                else:
                    timer_class = ""
                    timer_icon = "⏱️"
                
                st.markdown(f"""
                <div class="session-timer {timer_class}">
                    {timer_icon} {minutes:02d}:{seconds:02d}
                </div>
                """, unsafe_allow_html=True)
                
                if remaining <= 0:
                    st.rerun()
        
        with cols[2]:
            # زر دخول المشرف (فقط إذا لم يكن مشرف بالفعل)
            if not st.session_state.is_admin:
                with st.expander("🔐 دخول المشرف"):
                    admin_pass = st.text_input("كلمة المرور", type="password", key="admin_login")
                    if st.button("دخول"):
                        if admin_pass == st.secrets["admin_password"]:
                            st.session_state.is_admin = True
                            st.success("✅ تم تسجيل الدخول كمشرف")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ كلمة مرور خاطئة")

# ==========================================
# حالات الوصول
# ==========================================

if status == False:
    # شخص آخر يستخدم النظام
    st.markdown("""
    <div class="alert-box">
        <div class="alert-icon">⏳</div>
        <h2 style="color: #e67e22;">المكتبة مشغولة حالياً</h2>
        <p style="font-size: 1.1rem; color: #7f8c8d;">
            هناك باحث آخر يستخدم المكتبة الآن.<br>
            يرجى الانتظار حتى ينتهي من جلسته.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # زر دخول المشرف للتحكم
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.expander("🔐 دخول المشرف للتحكم"):
            admin_pass = st.text_input("كلمة المرور", type="password", key="admin_override")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("دخول وإغلاق الجلسة", use_container_width=True):
                    if admin_pass == st.secrets["admin_password"]:
                        state.locked = False
                        state.current_user_token = None
                        st.session_state.is_admin = True
                        st.success("✅ تم إغلاق الجلسة السابقة")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ كلمة مرور خاطئة")
            with col_b:
                if st.button("تحديث", use_container_width=True):
                    st.rerun()

elif status == "READY_TO_ENTER":
    # الصفحة الرئيسية - محرك البحث
    st.markdown("""
    <div class="main-container">
        <div class="logo-container">
            <div class="main-logo">📚</div>
            <h1 class="main-title">المكتبة الرقمية</h1>
            <p class="main-subtitle">ابحث في آلاف الكتب والمراجع العلمية</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # صندوق البحث
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    search_query = st.text_input(
        "ابحث عن كتاب",
        placeholder="ابحث عن كتاب، مؤلف، أو موضوع...",
        label_visibility="collapsed",
        key="main_search"
    )
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        search_button = st.button("🔍 بحث", use_container_width=True, type="primary")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if search_button and search_query:
        state.locked = True
        state.current_user_token = st.session_state.user_token
        state.last_activity = time.time()
        st.session_state.search_query = search_query
        st.rerun()
    elif search_button and not search_query:
        st.warning("⚠️ الرجاء إدخال كلمة بحث")

elif status in ["USER_ACCESS", "ADMIN_ACCESS"]:
    # صفحة البحث والنتائج
    st.markdown("""
    <div class="results-header">
        <h2 style="margin: 0; color: #2c3e50; font-family: 'Amiri', serif;">📚 نتائج البحث</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # صندوق بحث جديد
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        new_search = st.text_input(
            "بحث جديد",
            value=st.session_state.search_query,
            placeholder="ابحث عن كتاب آخر...",
            label_visibility="collapsed",
            key="results_search"
        )
    with col_btn:
        if st.button("🔍", use_container_width=True):
            if new_search:
                st.session_state.search_query = new_search
                st.session_state.current_page = 0
                clear_session_data()
                state.last_activity = time.time()
                st.rerun()
    
    # تنفيذ البحث
    if st.session_state.search_query:
        if 'search_results' not in st.session_state or not st.session_state.search_results:
            with st.spinner(f"🔍 جاري البحث عن: {st.session_state.search_query}"):
                start_time = time.time()
                results = search_books_async(st.session_state.search_query)
                search_time = time.time() - start_time
                
                st.session_state.search_results = results
                st.session_state.search_time = search_time
                state.last_activity = time.time()
        
        results = st.session_state.search_results
        
        if results:
            st.markdown(f"""
            <p class="results-count">
                تم العثور على {len(results)} نتيجة في {st.session_state.search_time:.2f} ثانية
            </p>
            """, unsafe_allow_html=True)
            
            # عرض النتائج مع pagination
            total_pages = (len(results) - 1) // ITEMS_PER_PAGE + 1
            start_idx = st.session_state.current_page * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, len(results))
            
            for result in results[start_idx:end_idx]:
                with st.container():
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="result-title">📖 {result['file_name']}</div>
                        <div class="result-meta">
                            📊 الحجم: {format_file_size(result['size'])} | 
                            📅 التاريخ: {result['date'].strftime('%Y-%m-%d')}
                        </div>
                        <div class="result-description">
                            {clean_description(result['caption'])[:200]}...
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        if st.button(f"📥 تحميل", key=f"dl_{result['id']}"):
                            buffer, file_name = download_book_to_memory(result['id'])
                            if buffer:
                                st.download_button(
                                    label="💾 حفظ الملف",
                                    data=buffer,
                                    file_name=file_name,
                                    mime="application/pdf",
                                    key=f"save_{result['id']}"
                                )
                                buffer.close()
                    
                    with col2:
                        if result['file_name'].lower().endswith('.pdf'):
                            if st.button(f"📄 عدد الصفحات", key=f"pages_{result['id']}"):
                                pages = get_pdf_page_count(result['id'])
                                if pages:
                                    st.info(f"📄 عدد الصفحات: {pages}")
                    
                    with col3:
                        if result['file_name'].lower().endswith('.pdf'):
                            if st.button(f"👁️ معاينة", key=f"preview_{result['id']}"):
                                img = get_first_page_preview(result['id'])
                                if img:
                                    st.image(img, caption="الصفحة الأولى", use_container_width=True)
                    
                    st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)
                    state.last_activity = time.time()
            
            # أزرار التنقل بين الصفحات
            if total_pages > 1:
                st.markdown("<br>", unsafe_allow_html=True)
                cols = st.columns([1, 2, 1, 2, 1])
                
                with cols[1]:
                    if st.session_state.current_page > 0:
                        if st.button("⏮️ السابق", use_container_width=True):
                            st.session_state.current_page -= 1
                            state.last_activity = time.time()
                            st.rerun()
                
                with cols[2]:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 0.7rem; background: white; 
                         border-radius: 8px; border: 1px solid #e0e0e0;">
                        صفحة {st.session_state.current_page + 1} من {total_pages}
                    </div>
                    """, unsafe_allow_html=True)
                
                with cols[3]:
                    if st.session_state.current_page < total_pages - 1:
                        if st.button("التالي ⏭️", use_container_width=True):
                            st.session_state.current_page += 1
                            state.last_activity = time.time()
                            st.rerun()
        
        else:
            st.markdown("""
            <div class="alert-box">
                <div class="alert-icon">🔍</div>
                <h2 style="color: #7f8c8d;">لم يتم العثور على نتائج</h2>
                <p style="font-size: 1.1rem; color: #95a5a6;">
                    لم نعثر على أي كتب تطابق بحثك.<br>
                    جرّب استخدام كلمات مختلفة أو أكثر عمومية.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 بحث جديد", use_container_width=True):
                    st.session_state.search_query = ""
                    clear_session_data()
                    state.locked = False
                    state.current_user_token = None
                    st.rerun()

# تحديث تلقائي للعداد
if status in ["USER_ACCESS", "ADMIN_ACCESS"] and state.locked:
    time.sleep(1)
    st.rerun()