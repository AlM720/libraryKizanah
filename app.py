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
from collections import defaultdict
from streamlit_autorefresh import st_autorefresh

# تفعيل تعدد المهام لبيئة Streamlit
nest_asyncio.apply()

# تحديث تلقائي كل ثانية (لعمل العداد)
counter = st_autorefresh(interval=1000, key="counter")

# إعداد الصفحة
st.set_page_config(
    page_title="باحث الكتب - المكتبة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تصميم CSS محسن مع خلفية جديدة وأيقونات Font Awesome ---
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" integrity="sha512-iecdLmaskl7CVkqkXNQ/ZH/XLlvWZOJyj7Yy7tcenmpD1ypASozpmT/E0iPtmFIB46ZmdtAc9eNBvH0H/ZpiBw==" crossorigin="anonymous" referrerpolicy="no-referrer" />
<style>
    /* خلفية جديدة - مكتبة أنيقة */
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?q=80&w=3000&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        color: #2C3E50;
        font-family: 'Segoe UI', 'Noto Sans Arabic', Tahoma, Geneva, Verdana, sans-serif;
        direction: rtl;
    }
    
    /* تحسينات RTL */
    .rtl-text {
        direction: rtl;
        text-align: right;
        font-family: 'Noto Sans Arabic', 'Segoe UI', sans-serif;
    }
    
    /* هيكل الصفحة الرئيسي */
    .main-container {
        background-color: rgba(255, 255, 255, 0.92);
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(5px);
    }
    
    /* الهيدر الرئيسي */
    .header {
        background: linear-gradient(135deg, #2C3E50 0%, #4A6491 100%);
        padding: 30px;
        text-align: center;
        border-radius: 15px;
        margin-bottom: 30px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        color: white;
    }
    
    .header h1 {
        color: white;
        font-size: 36px;
        margin: 0;
        font-weight: 700;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
        font-family: 'Noto Sans Arabic', sans-serif;
    }
    
    .header p {
        color: #ECF0F1;
        font-size: 18px;
        margin: 10px 0 0;
        font-family: 'Noto Sans Arabic', sans-serif;
        opacity: 0.9;
    }
    
    /* بطاقة الترحيب */
    .welcome-card {
        background: linear-gradient(135deg, rgba(52, 152, 219, 0.95) 0%, rgba(41, 128, 185, 0.95) 100%);
        color: white;
        padding: 35px;
        border-radius: 15px;
        text-align: center;
        margin: 25px 0;
        box-shadow: 0 5px 20px rgba(41, 128, 185, 0.3);
        border: 2px solid rgba(255, 255, 255, 0.2);
    }
    
    .welcome-card h3 {
        font-size: 28px;
        margin-bottom: 15px;
        font-weight: 600;
        font-family: 'Noto Sans Arabic', sans-serif;
    }
    
    .welcome-card p {
        font-size: 18px;
        line-height: 1.8;
        margin-bottom: 20px;
        font-family: 'Noto Sans Arabic', sans-serif;
        opacity: 0.95;
    }
    
    .welcome-card h4 {
        font-size: 24px;
        margin-top: 20px;
        color: #FFD700;
        font-weight: 700;
        font-family: 'Noto Sans Arabic', sans-serif;
    }
    
    /* بطاقة النظام مشغول */
    .busy-card {
        background: linear-gradient(135deg, rgba(231, 76, 60, 0.95) 0%, rgba(192, 57, 43, 0.95) 100%);
        color: white;
        padding: 35px;
        border-radius: 15px;
        text-align: center;
        margin: 25px 0;
        box-shadow: 0 5px 20px rgba(192, 57, 43, 0.3);
        border: 2px solid rgba(255, 255, 255, 0.2);
    }
    
    .busy-card h3 {
        font-size: 28px;
        margin-bottom: 15px;
        font-weight: 600;
        font-family: 'Noto Sans Arabic', sans-serif;
    }
    
    .busy-card p {
        font-size: 18px;
        line-height: 1.8;
        margin-bottom: 15px;
        font-family: 'Noto Sans Arabic', sans-serif;
        opacity: 0.95;
    }
    
    /* عداد الوقت */
    .timer {
        font-size: 42px;
        font-weight: 800;
        color: #FFD700;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        margin: 20px 0;
        font-family: 'Segoe UI', monospace;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* الأزرار */
    .stButton > button {
        background: linear-gradient(135deg, #27AE60 0%, #219653 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 14px 28px;
        font-size: 18px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(39, 174, 96, 0.3);
        font-family: 'Noto Sans Arabic', sans-serif;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #219653 0%, #1E8449 100%);
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(39, 174, 96, 0.4);
    }
    
    /* البادج */
    .badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 25px;
        font-size: 14px;
        font-weight: bold;
        font-family: 'Noto Sans Arabic', sans-serif;
    }
    
    .badge-admin {
        background: linear-gradient(135deg, #E74C3C 0%, #C0392B 100%);
        color: white;
        box-shadow: 0 3px 6px rgba(231, 76, 60, 0.3);
    }
    
    .badge-user {
        background: linear-gradient(135deg, #3498DB 0%, #2980B9 100%);
        color: white;
        box-shadow: 0 3px 6px rgba(52, 152, 219, 0.3);
    }
    
    /* الإكسباندير */
    .stExpander {
        border: 1px solid rgba(52, 152, 219, 0.2);
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.95);
        margin: 10px 0;
    }
    
    .stExpander > div > div {
        font-family: 'Noto Sans Arabic', sans-serif !important;
    }
    
    /* التنبيهات */
    .stAlert {
        border-radius: 10px;
        padding: 15px;
        border: none;
        font-family: 'Noto Sans Arabic', sans-serif;
    }
    
    /* حاوية البحث */
    .search-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 25px;
        border-radius: 15px;
        margin: 20px 0;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(52, 152, 219, 0.1);
    }
    
    /* تحسينات للإدخال */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #BDC3C7;
        padding: 12px 16px;
        font-size: 16px;
        font-family: 'Noto Sans Arabic', sans-serif;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3498DB;
        box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
    }
    
    /* بطاقة النتائج */
    .result-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(245, 245, 245, 0.95) 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid rgba(52, 152, 219, 0.2);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .result-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
    }
    
    /* أيقونات */
    .icon-large {
        font-size: 48px;
        margin-bottom: 20px;
        display: block;
    }
    
    .icon-book { color: #3498DB; }
    .icon-clock { color: #E67E22; }
    .icon-lock { color: #E74C3C; }
    .icon-search { color: #27AE60; }
    .icon-trash { color: #C0392B; }
    .icon-refresh { color: #2980B9; }
    .icon-door-open { color: #2ECC71; }
    .icon-download { color: #9B59B6; }
    .icon-eye { color: #3498DB; }
    .icon-file { color: #E67E22; }
    
    /* تحسين التبويبات */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        direction: rtl;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-family: 'Noto Sans Arabic', sans-serif;
        font-weight: 600;
        font-size: 16px;
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
    }
    
    /* التقدم */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #3498DB, #2ECC71);
    }
</style>
""", unsafe_allow_html=True)

# --- ⚙️ إعدادات النظام ---
TIMEOUT_SECONDS = 180

required_secrets = ["api_id", "api_hash", "session_string", "channel_id", "admin_password", "key"]
if not all(key in st.secrets for key in required_secrets):
    st.error("⚠️ خطأ: تأكد من إعداد ملف secrets.toml بكامل البيانات (بما في ذلك key).")
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

# --- دالة تنظيف الذاكرة ---
def clear_session_data():
    """تنظيف البيانات المؤقتة والذاكرة"""
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

status = check_access()

# ==========================================
# 🛑 شاشة الانتظار (النظام مشغول)
# ==========================================
if status == False:
    st.markdown("""
    <div class="header">
        <h1>المكتبة الرقمية</h1>
        <p>نظام البحث في الكتب والمراجع</p>
    </div>
    """, unsafe_allow_html=True)
    
    time_passed = int(time.time() - state.last_activity)
    time_left = max(0, TIMEOUT_SECONDS - time_passed)
    
    st.markdown(f"""
    <div class="busy-card">
        <i class="fas fa-pause-circle icon-large icon-clock"></i>
        <h3>النظام مشغول حالياً</h3>
        <p>يستخدم أحد الباحثين النظام في الوقت الحالي.</p>
        <p>للحفاظ على استقرار الخدمة، يُسمح بدخول مستخدم واحد فقط في كل مرة.</p>
        
        <div class="timer">{time_left}</div>
        
        <p>سيتم إتاحة النظام تلقائياً عند انتهاء المدة المحددة</p>
    </div>
    """, unsafe_allow_html=True)
    
    # زر تحديث الحالة
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("<i class='fas fa-sync-alt'></i> تحديث الحالة", use_container_width=True):
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # قسم دخول المسؤول - أصبح أكثر وضوحاً
    st.markdown("""
    <div class="main-container">
        <div style="text-align: center; margin-bottom: 20px;">
            <h3 style="color: #2C3E50;"><i class="fas fa-user-shield"></i> دخول المسؤول</h3>
            <p style="color: #7F8C8D;">أدخل كلمة المرور للدخول لوضع الإدارة</p>
        </div>
    """, unsafe_allow_html=True)
    
    # حاوية دخول المسؤول
    admin_container = st.container()
    with admin_container:
        col_pass1, col_pass2, col_pass3 = st.columns([1, 2, 1])
        with col_pass2:
            password_attempt = st.text_input("كلمة مرور المسؤول:", type="password", key="admin_pass_locked")
            if st.button("الدخول لوضع الإدارة", use_container_width=True, type="secondary"):
                if password_attempt == st.secrets["admin_password"]:
                    st.session_state.is_admin = True
                    st.success("تم التحقق من الهوية")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # صندوق إنهاء الجلسة للمشرف (مخفي في توسيع)
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("<i class='fas fa-cog'></i> لوحة تحكم المشرف (إدارة الجلسات)"):
        st.markdown("**إنهاء الجلسة الحالية قسرياً**")
        st.caption("استخدم هذا الخيار لإنهاء جلسة المستخدم الحالي فوراً")
        
        supervisor_key = st.text_input("مفتاح المشرف:", type="password", key="supervisor_key_waiting")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("إنهاء الجلسة الحالية", use_container_width=True, type="primary"):
                if supervisor_key == st.secrets["key"]:
                    state.locked = False
                    state.current_user_token = None
                    clear_session_data()
                    st.success("تم إنهاء الجلسة بنجاح")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("مفتاح المشرف غير صحيح")
    
    st.stop()

# ==========================================
# 👋 شاشة الترحيب (النظام متاح)
# ==========================================
elif status == "READY_TO_ENTER":
    st.markdown("""
    <div class="header">
        <h1>المكتبة الرقمية</h1>
        <p>نظام البحث في الكتب والمراجع</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="welcome-card">
        <i class="fas fa-door-open icon-large icon-door-open"></i>
        <h3>مرحباً بك في المكتبة الرقمية</h3>
        <p>يوفر لك هذا النظام إمكانية البحث في آلاف الكتب والمراجع العلمية والأدبية<br>
        من مختلف المجالات المعرفية. استخدم محرك البحث للعثور على الكتاب المطلوب<br>
        وتحميله مباشرة إلى جهازك.</p>
        <h4>النظام متاح الآن للاستخدام</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # زر بدء الاستخدام
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("<i class='fas fa-book-open'></i> بدء استخدام المكتبة", use_container_width=True, type="primary"):
            state.locked = True
            state.current_user_token = st.session_state.user_token
            state.last_activity = time.time()
            st.rerun()
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # قسم دخول المسؤول - منفصل وواضح
    st.markdown("""
    <div class="main-container">
        <div style="text-align: center; margin-bottom: 25px;">
            <h3 style="color: #2C3E50;"><i class="fas fa-user-shield"></i> دخول المسؤول</h3>
            <p style="color: #7F8C8D;">الدخول لوضع إدارة النظام والملفات</p>
        </div>
        
        <div style="max-width: 500px; margin: 0 auto;">
    """, unsafe_allow_html=True)
    
    password_attempt = st.text_input("كلمة مرور المسؤول:", type="password", key="admin_pass_open")
    
    col_admin1, col_admin2, col_admin3 = st.columns([1, 1, 1])
    with col_admin2:
        if st.button("دخول المسؤول", use_container_width=True, type="secondary"):
            if password_attempt == st.secrets["admin_password"]:
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("كلمة المرور غير صحيحة")
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    st.stop()

# ==========================================
# ✅ التطبيق الرئيسي
# ==========================================

# الهيدر الرئيسي
st.markdown("""
<div class="header">
    <h1>المكتبة الرقمية</h1>
    <p>نظام البحث في الكتب والمراجع</p>
</div>
""", unsafe_allow_html=True)

# شريط المعلومات العلوي
time_left_session = max(0, TIMEOUT_SECONDS - int(time.time() - state.last_activity))

if st.session_state.is_admin:
    status_badge = '<span class="badge badge-admin"><i class="fas fa-user-shield"></i> وضع الإدارة</span>'
else:
    status_badge = f'<span class="badge badge-user"><i class="fas fa-clock"></i> وقت متبقي: {time_left_session} ثانية</span>'

col_info1, col_info2, col_info3 = st.columns([2, 5, 2])

with col_info1:
    st.markdown(f'<div style="text-align: right; padding-top: 10px;">{status_badge}</div>', unsafe_allow_html=True)

with col_info3:
    if st.button("<i class='fas fa-sign-out-alt'></i> إنهاء الجلسة", use_container_width=True, type="secondary"):
        if st.session_state.is_admin:
            st.session_state.is_admin = False
        else:
            state.locked = False
            state.current_user_token = None
        clear_session_data()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# تحذير للمدير
if status == "ADMIN_ACCESS" and state.locked and state.current_user_token != st.session_state.user_token:
    st.warning("⚠️ تنبيه: يوجد مستخدم نشط آخر. الاستخدام المتزامن قد يسبب مشاكل في النظام.")
    st.markdown("<br>", unsafe_allow_html=True)

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
            st.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
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
    """حساب عدد صفحات الكتاب PDF"""
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
    """استخراج أول صفحة من PDF كصورة"""
    try:
        buffer, file_name = download_book_to_memory(message_id)
        if buffer and file_name.lower().endswith('.pdf'):
            # فتح PDF باستخدام PyMuPDF
            pdf_document = fitz.open(stream=buffer.read(), filetype="pdf")
            
            # الحصول على الصفحة الأولى
            if len(pdf_document) > 0:
                first_page = pdf_document[0]
                
                # تحويل الصفحة إلى صورة
                zoom = 2
                mat = fitz.Matrix(zoom, zoom)
                pix = first_page.get_pixmap(matrix=mat)
                
                # تحويل إلى PIL Image
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

# --- دوال إدارة المكررات ---
async def scan_for_duplicates():
    """مسح القناة والبحث عن الملفات المكررة"""
    client = await get_client()
    files_by_size = defaultdict(list)
    
    try:
        entity = await client.get_entity(channel_id)
        
        # جمع جميع الملفات
        async for message in client.iter_messages(entity):
            if message.file:
                file_info = {
                    'id': message.id,
                    'name': message.file.name or 'بدون اسم',
                    'size': message.file.size,
                    'date': message.date,
                    'caption': message.text or ''
                }
                files_by_size[message.file.size].append(file_info)
        
        # البحث عن المكررات (نفس الحجم)
        potential_duplicates = []
        for size, files in files_by_size.items():
            if len(files) > 1:  # أكثر من ملف بنفس الحجم
                potential_duplicates.append(files)
        
        return potential_duplicates
        
    except Exception as e:
        st.error(f"خطأ في المسح: {e}")
        return []
    finally:
        await client.disconnect()

async def delete_file(message_id):
    """حذف ملف من القناة"""
    client = await get_client()
    try:
        entity = await client.get_entity(channel_id)
        await client.delete_messages(entity, message_id)
        return True
    except Exception as e:
        st.error(f"خطأ في الحذف: {e}")
        return False
    finally:
        await client.disconnect()

# --- حالة الإدارة ---
if 'admin_duplicate_groups' not in st.session_state:
    st.session_state.admin_duplicate_groups = []

if 'admin_scan_completed' not in st.session_state:
    st.session_state.admin_scan_completed = False

if 'admin_current_page' not in st.session_state:
    st.session_state.admin_current_page = 0

# --- واجهة المستخدم الرئيسية مع التبويبات ---
st.markdown("---")

# حاوية البحث الرئيسية
with st.container():
    if st.session_state.is_admin:
        tab_search, tab_admin = st.tabs(["🔍 البحث في الكتب", "⚙️ إدارة المكررات"])
        
        with tab_search:
            if 'search_results' not in st.session_state:
                st.session_state.search_results = []
            if 'search_time' not in st.session_state:
                st.session_state.search_time = None

            st.markdown("""
            <div class="search-container">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h3 style="color: #2C3E50;"><i class="fas fa-search icon-search"></i> البحث في الكتب</h3>
                    <p style="color: #7F8C8D;">ابحث عن الكتب والمراجع العلمية والأدبية</p>
                </div>
            """, unsafe_allow_html=True)
            
            query = st.text_input("أدخل اسم الكتاب أو الكلمة المفتاحية:", key="search_query")
            
            col_btn = st.columns([1, 1, 1])
            with col_btn[1]:
                if st.button("<i class='fas fa-search'></i> بدء البحث", use_container_width=True, type="primary"):
                    with st.spinner("جاري البحث في المكتبة..."):
                        results = search_books_async(query)
                        st.session_state.search_results = results
                        st.session_state.search_time = time.time()

            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.session_state.search_results:
                st.markdown(f"""
                <div style="text-align: center; padding: 15px; background-color: rgba(52, 152, 219, 0.1); border-radius: 10px; margin: 20px 0;">
                    <h4 style="color: #2C3E50;"><i class="fas fa-book"></i> نتائج البحث</h4>
                    <p style="color: #3498DB; font-size: 18px; font-weight: bold;">تم العثور على {len(st.session_state.search_results)} نتيجة</p>
                </div>
                """, unsafe_allow_html=True)
                
                for idx, result in enumerate(st.session_state.search_results, 1):
                    with st.expander(f"📚 {result['file_name']}", expanded=False):
                        st.markdown(f"""
                        <div class="result-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                <div>
                                    <h5 style="color: #2C3E50; margin: 0;"><i class="fas fa-file-alt"></i> {result['file_name']}</h5>
                                    <p style="color: #7F8C8D; margin: 5px 0;"><i class="fas fa-calendar-alt"></i> {result['date'].strftime('%Y-%m-%d %H:%M')}</p>
                                </div>
                                <div style="background-color: #3498DB; color: white; padding: 5px 12px; border-radius: 20px; font-size: 14px;">
                                    <i class="fas fa-weight"></i> {result['size'] / (1024*1024):.2f} ميجابايت
                                </div>
                            </div>
                            
                            <div style="background-color: rgba(236, 240, 241, 0.5); padding: 12px; border-radius: 8px; margin: 10px 0;">
                                <p style="color: #34495E; margin: 0; line-height: 1.6;"><strong>الوصف:</strong> {result['caption'][:250] if result['caption'] else 'لا يوجد وصف'}</p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("📥 تحميل الكتاب", key=f"dl_{result['id']}", use_container_width=True):
                                with st.spinner("جاري تحميل الكتاب..."):
                                    buffer, file_name = download_book_to_memory(result['id'])
                                    if buffer:
                                        st.download_button(
                                            "💾 حفظ الملف",
                                            data=buffer,
                                            file_name=file_name,
                                            mime="application/octet-stream",
                                            use_container_width=True
                                        )
                        
                        with col2:
                            if st.button("📄 عدد الصفحات", key=f"pages_{result['id']}", use_container_width=True):
                                with st.spinner("جاري حساب عدد الصفحات..."):
                                    pages = get_pdf_page_count(result['id'])
                                    if pages:
                                        st.success(f"📖 عدد الصفحات: {pages}")
                                    else:
                                        st.warning("لم يتم العثور على عدد الصفحات")
                        
                        with col3:
                            if st.button("👁️ معاينة الصفحة الأولى", key=f"prev_{result['id']}", use_container_width=True):
                                with st.spinner("جاري تحضير المعاينة..."):
                                    img = get_first_page_preview(result['id'])
                                    if img:
                                        st.image(img, caption="الصفحة الأولى من الكتاب", use_column_width=True)
                                    else:
                                        st.warning("تعذر إنشاء معاينة للصفحة الأولى")
            
            elif st.session_state.search_time:
                st.info("🔍 لم يتم العثور على نتائج مطابقة لبحثك. حاول بكلمات مفتاحية أخرى.")
        
        with tab_admin:
            st.markdown("""
            <div class="search-container">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h3 style="color: #2C3E50;"><i class="fas fa-copy icon-book"></i> إدارة الملفات المكررة</h3>
                    <p style="color: #7F8C8D;">نظام الكشف والحذف الذكي للملفات المكررة</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.info("🔒 **الجلسات الأخرى متوقفة** - أنت الوحيد المسموح له بالدخول حالياً")
            
            st.markdown("---")
            
            if not st.session_state.admin_scan_completed:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown("""
                    <div style="text-align: center; padding: 20px;">
                        <i class="fas fa-search-plus icon-large" style="color: #3498DB;"></i>
                        <h4>ابدأ عملية المسح</h4>
                        <p>سيتم فحص جميع الملفات في القناة للبحث عن المكررات</p>
                        <p style="color: #7F8C8D; font-size: 14px;">هذه العملية قد تستغرق بعض الوقت حسب عدد الملفات</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("<i class='fas fa-play-circle'></i> بدء المسح الآن", use_container_width=True, type="primary"):
                        with st.spinner("🔍 جاري مسح القناة... قد يستغرق بعض الوقت"):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            duplicates = loop.run_until_complete(scan_for_duplicates())
                            loop.close()
                            
                            st.session_state.admin_duplicate_groups = duplicates
                            st.session_state.admin_scan_completed = True
                            st.session_state.admin_current_page = 0
                            st.rerun()
            else:
                if len(st.session_state.admin_duplicate_groups) == 0:
                    st.markdown("""
                    <div style="text-align: center; padding: 40px; background-color: rgba(46, 204, 113, 0.1); border-radius: 15px; margin: 20px 0;">
                        <i class="fas fa-check-circle icon-large" style="color: #27AE60;"></i>
                        <h2 style="color: #27AE60;">رائع!</h2>
                        <p style="color: #2C3E50; font-size: 18px;">لا توجد ملفات مكررة في القناة</p>
                        <p style="color: #7F8C8D;">جميع الملفات فريدة ولا تحتاج إلى تنظيف</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("<i class='fas fa-sync-alt icon-refresh'></i> إعادة المسح", use_container_width=True):
                        st.session_state.admin_scan_completed = False
                        st.session_state.admin_duplicate_groups = []
                        st.session_state.admin_current_page = 0
                        st.rerun()
                else:
                    total_groups = len(st.session_state.admin_duplicate_groups)
                    st.success(f"✅ تم العثور على **{total_groups}** مجموعة من الملفات المحتملة المكررة")
                    
                    if st.button("<i class='fas fa-sync-alt icon-refresh'></i> إعادة المسح", use_container_width=True):
                        st.session_state.admin_scan_completed = False
                        st.session_state.admin_duplicate_groups = []
                        st.session_state.admin_current_page = 0
                        st.rerun()
                    
                    st.markdown("---")
                    
                    # تجزئة العرض: 3 مجموعات لكل صفحة
                    page_size = 3
                    start_idx = st.session_state.admin_current_page * page_size
                    end_idx = start_idx + page_size
                    displayed_groups = st.session_state.admin_duplicate_groups[start_idx:end_idx]
                    
                    # عرض المجموعات المعروضة
                    for idx, group in enumerate(displayed_groups, start_idx + 1):
                        st.markdown(f"""
                        <div style="padding: 20px; background-color: rgba(255, 255, 255, 0.95); border-radius: 12px; margin-bottom: 25px; border: 2px solid rgba(231, 76, 60, 0.2);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                <h4 style="color: #E74C3C; margin: 0;"><i class="fas fa-exclamation-triangle"></i> مجموعة مكررة #{idx}</h4>
                                <div style="background-color: #E74C3C; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px;">
                                    {len(group)} ملف
                                </div>
                            </div>
                            <p style="color: #7F8C8D; margin: 5px 0;"><strong><i class="fas fa-weight"></i> الحجم المشترك:</strong> {group[0]['size'] / (1024*1024):.2f} ميجابايت</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # عرض كل ملف في المجموعة
                        for file_idx, file in enumerate(group, 1):
                            with st.expander(f"📄 الملف {file_idx}: {file['name']}", expanded=True):
                                st.markdown(f"""
                                <div style="padding: 15px; background-color: rgba(241, 242, 246, 0.5); border-radius: 8px; margin: 10px 0;">
                                    <p style="color: #2C3E50; margin: 5px 0;"><strong><i class="fas fa-file"></i> الاسم:</strong> {file['name']}</p>
                                    <p style="color: #7F8C8D; margin: 5px 0;"><strong><i class="fas fa-weight"></i> الحجم:</strong> {file['size'] / (1024*1024):.2f} ميجابايت</p>
                                    <p style="color: #7F8C8D; margin: 5px 0;"><strong><i class="fas fa-calendar-alt"></i> التاريخ:</strong> {file['date'].strftime('%Y-%m-%d %H:%M')}</p>
                                    <div style="background-color: rgba(236, 240, 241, 0.5); padding: 10px; border-radius: 6px; margin: 10px 0;">
                                        <p style="color: #34495E; margin: 0; font-size: 14px;"><strong><i class="fas fa-align-left"></i> الوصف:</strong> {file['caption'][:150] if file['caption'] else 'لا يوجد وصف'}</p>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    if st.button(f"فحص عدد الصفحات", key=f"admin_check_pages_{file['id']}", use_container_width=True):
                                        with st.spinner("جاري الفحص..."):
                                            pages = get_pdf_page_count(file['id'])
                                            if pages:
                                                st.success(f"📄 عدد الصفحات: {pages}")
                                            else:
                                                st.warning("⚠️ لم نتمكن من حساب عدد الصفحات (قد لا يكون PDF)")
                                
                                with col2:
                                    delete_key = f"admin_delete_{file['id']}"
                                    if st.button(f"<i class='fas fa-trash'></i> حذف الملف", key=delete_key, use_container_width=True, type="secondary"):
                                        st.warning(f"⚠️ هل أنت متأكد من حذف الملف: {file['name']}?")
                                        confirm_key = f"admin_confirm_{file['id']}"
                                        if st.button(f"نعم، احذف نهائياً", key=confirm_key, use_container_width=True):
                                            with st.spinner("جاري حذف الملف..."):
                                                loop = asyncio.new_event_loop()
                                                asyncio.set_event_loop(loop)
                                                success = loop.run_until_complete(delete_file(file['id']))
                                                loop.close()
                                                
                                                if success:
                                                    st.success("✅ تم الحذف بنجاح!")
                                                    time.sleep(1)
                                                    # إعادة المسح بعد الحذف
                                                    st.session_state.admin_scan_completed = False
                                                    st.session_state.admin_duplicate_groups = []
                                                    st.session_state.admin_current_page = 0
                                                    st.rerun()
                                                else:
                                                    st.error("❌ فشل الحذف")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                    
                    # أزرار التنقل بين الصفحات
                    if total_groups > page_size:
                        col_prev, col_info, col_next = st.columns([1, 2, 1])
                        with col_prev:
                            if st.session_state.admin_current_page > 0:
                                if st.button("<i class='fas fa-arrow-left'></i> السابق", use_container_width=True):
                                    st.session_state.admin_current_page -= 1
                                    st.rerun()
                        with col_info:
                            st.markdown(f"""
                            <div style="text-align: center; padding: 10px; color: #7F8C8D;">
                                الصفحة {st.session_state.admin_current_page + 1} من {((total_groups - 1) // page_size) + 1}
                            </div>
                            """, unsafe_allow_html=True)
                        with col_next:
                            if end_idx < total_groups:
                                if st.button("التالي <i class='fas fa-arrow-right'></i>", use_container_width=True):
                                    st.session_state.admin_current_page += 1
                                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    else:
        # واجهة البحث فقط للمستخدم العادي
        if 'search_results' not in st.session_state:
            st.session_state.search_results = []
        if 'search_time' not in st.session_state:
            st.session_state.search_time = None

        st.markdown("""
        <div class="search-container">
            <div style="text-align: center; margin-bottom: 20px;">
                <h3 style="color: #2C3E50;"><i class="fas fa-search icon-search"></i> البحث في الكتب</h3>
                <p style="color: #7F8C8D;">ابحث عن الكتب والمراجع العلمية والأدبية</p>
            </div>
        """, unsafe_allow_html=True)
        
        query = st.text_input("أدخل اسم الكتاب أو الكلمة المفتاحية:", key="search_query_nonadmin")
        
        col_btn = st.columns([1, 1, 1])
        with col_btn[1]:
            if st.button("<i class='fas fa-search'></i> بدء البحث", use_container_width=True, type="primary"):
                with st.spinner("جاري البحث في المكتبة..."):
                    results = search_books_async(query)
                    st.session_state.search_results = results
                    st.session_state.search_time = time.time()

        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.session_state.search_results:
            st.markdown(f"""
            <div style="text-align: center; padding: 15px; background-color: rgba(52, 152, 219, 0.1); border-radius: 10px; margin: 20px 0;">
                <h4 style="color: #2C3E50;"><i class="fas fa-book"></i> نتائج البحث</h4>
                <p style="color: #3498DB; font-size: 18px; font-weight: bold;">تم العثور على {len(st.session_state.search_results)} نتيجة</p>
            </div>
            """, unsafe_allow_html=True)
            
            for idx, result in enumerate(st.session_state.search_results, 1):
                with st.expander(f"📚 {result['file_name']}", expanded=False):
                    st.markdown(f"""
                    <div class="result-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <div>
                                <h5 style="color: #2C3E50; margin: 0;"><i class="fas fa-file-alt"></i> {result['file_name']}</h5>
                                <p style="color: #7F8C8D; margin: 5px 0;"><i class="fas fa-calendar-alt"></i> {result['date'].strftime('%Y-%m-%d %H:%M')}</p>
                            </div>
                            <div style="background-color: #3498DB; color: white; padding: 5px 12px; border-radius: 20px; font-size: 14px;">
                                <i class="fas fa-weight"></i> {result['size'] / (1024*1024):.2f} ميجابايت
                            </div>
                        </div>
                        
                        <div style="background-color: rgba(236, 240, 241, 0.5); padding: 12px; border-radius: 8px; margin: 10px 0;">
                            <p style="color: #34495E; margin: 0; line-height: 1.6;"><strong>الوصف:</strong> {result['caption'][:250] if result['caption'] else 'لا يوجد وصف'}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("📥 تحميل الكتاب", key=f"dl_nonadmin_{result['id']}", use_container_width=True):
                            with st.spinner("جاري تحميل الكتاب..."):
                                buffer, file_name = download_book_to_memory(result['id'])
                                if buffer:
                                    st.download_button(
                                        "💾 حفظ الملف",
                                        data=buffer,
                                        file_name=file_name,
                                        mime="application/octet-stream",
                                        use_container_width=True
                                    )
                    
                    with col2:
                        if st.button("📄 عدد الصفحات", key=f"pages_nonadmin_{result['id']}", use_container_width=True):
                            with st.spinner("جاري حساب عدد الصفحات..."):
                                pages = get_pdf_page_count(result['id'])
                                if pages:
                                    st.success(f"📖 عدد الصفحات: {pages}")
                                else:
                                    st.warning("لم يتم العثور على عدد الصفحات")
                    
                    with col3:
                        if st.button("👁️ معاينة الصفحة الأولى", key=f"prev_nonadmin_{result['id']}", use_container_width=True):
                            with st.spinner("جاري تحضير المعاينة..."):
                                img = get_first_page_preview(result['id'])
                                if img:
                                    st.image(img, caption="الصفحة الأولى من الكتاب", use_column_width=True)
                                else:
                                    st.warning("تعذر إنشاء معاينة للصفحة الأولى")
        
        elif st.session_state.search_time:
            st.info("🔍 لم يتم العثور على نتائج مطابقة لبحثك. حاول بكلمات مفتاحية أخرى.")

# تذييل الصفحة
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 20px; color: #7F8C8D; font-size: 14px;">
    <p><i class="fas fa-copyright"></i> المكتبة الرقمية - نظام البحث في الكتب والمراجع</p>
    <p>تم التطوير بواسطة المُبَرْمِج</p>
</div>
""", unsafe_allow_html=True)