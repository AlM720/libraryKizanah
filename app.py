import streamlit as st
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import nest_asyncio
import io
import time
import uuid

# تفعيل تعدد المهام لبيئة Streamlit
nest_asyncio.apply()

# إعداد الصفحة
st.set_page_config(
    page_title="باحث الكتب - المكتبة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تصميم CSS احترافي يشبه المكتبات الأكاديمية ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Tajawal:wght@300;400;500;700&display=swap');
    
    * {
        font-family: 'Tajawal', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Amiri', serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* الهيدر الأكاديمي */
    .library-header {
        background: linear-gradient(to bottom, #2c3e50 0%, #34495e 100%);
        padding: 1.5rem 0;
        margin-bottom: 2rem;
        border-bottom: 3px solid #95a5a6;
    }
    
    .library-title {
        color: #ecf0f1;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin: 0;
        letter-spacing: 1px;
    }
    
    .library-subtitle {
        color: #bdc3c7;
        text-align: center;
        font-size: 1rem;
        margin-top: 0.5rem;
        font-weight: 300;
    }
    
    /* شريط المعلومات */
    .info-bar {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        padding: 0.8rem 1.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* صندوق البحث الأكاديمي */
    .search-container {
        background: white;
        border: 2px solid #dee2e6;
        border-radius: 2px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    
    .search-label {
        color: #2c3e50;
        font-size: 1.1rem;
        font-weight: 500;
        margin-bottom: 1rem;
        display: block;
    }
    
    /* بطاقة الكتاب - تصميم أرشيفي */
    .book-item {
        background: white;
        border: 1px solid #e0e0e0;
        border-right: 4px solid #7f8c8d;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }
    
    .book-item:hover {
        border-right-color: #34495e;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .book-number {
        color: #95a5a6;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    
    .book-main-title {
        color: #2c3e50;
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
        line-height: 1.4;
    }
    
    .book-metadata {
        color: #7f8c8d;
        font-size: 0.9rem;
        margin-bottom: 1rem;
        padding: 0.5rem 0;
        border-top: 1px solid #ecf0f1;
        border-bottom: 1px solid #ecf0f1;
    }
    
    .book-metadata span {
        margin-left: 1.5rem;
    }
    
    .book-description {
        color: #5a6c7d;
        font-size: 0.95rem;
        line-height: 1.7;
        margin-bottom: 1rem;
        text-align: justify;
    }
    
    /* الأزرار الكلاسيكية */
    .stButton>button {
        background: #34495e !important;
        color: white !important;
        border: none !important;
        border-radius: 2px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 500 !important;
        font-size: 1.05rem !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton>button:hover {
        background: #2c3e50 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
    }
    
    /* مدخلات النصوص */
    .stTextInput>div>div>input {
        border: 1px solid #ced4da !important;
        border-radius: 2px !important;
        padding: 0.7rem 1rem !important;
        font-size: 1rem !important;
        background: #fafafa !important;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #7f8c8d !important;
        background: white !important;
    }
    
    /* صندوق النتائج */
    .results-header {
        background: #ecf0f1;
        border-left: 4px solid #34495e;
        padding: 1rem 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    .results-title {
        color: #2c3e50;
        font-size: 1.3rem;
        font-weight: 600;
        margin: 0;
    }
    
    .results-stats {
        color: #7f8c8d;
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }
    
    /* شاشة الانتظار */
    .waiting-container {
        background: white;
        border: 2px solid #e74c3c;
        padding: 3rem;
        text-align: center;
        margin: 3rem auto;
        max-width: 600px;
    }
    
    .waiting-title {
        color: #c0392b;
        font-size: 1.8rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .waiting-text {
        color: #7f8c8d;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    
    .timer-display {
        background: #ecf0f1;
        border: 1px solid #bdc3c7;
        border-radius: 2px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        font-size: 2.5rem;
        font-weight: 700;
        color: #34495e;
    }
    
    /* شاشة الترحيب */
    .welcome-box {
        background: white;
        border: 1px solid #dee2e6;
        padding: 3rem;
        text-align: center;
        margin: 2rem auto;
        max-width: 700px;
    }
    
    .welcome-title {
        color: #2c3e50;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    .welcome-description {
        color: #7f8c8d;
        font-size: 1.1rem;
        line-height: 1.8;
        margin-bottom: 2rem;
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #27ae60;
        margin-left: 0.5rem;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* شارة الحالة */
    .badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        background: #ecf0f1;
        color: #2c3e50;
        border-radius: 2px;
        font-size: 0.85rem;
        font-weight: 500;
        border: 1px solid #bdc3c7;
    }
    
    .badge-admin {
        background: #34495e;
        color: white;
        border-color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

# --- ⚙️ إعدادات النظام ---
TIMEOUT_SECONDS = 180

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

# --- 🔐 منطق الحارس ---
def check_access():
    current_time = time.time()
    
    if state.locked and (current_time - state.last_activity > TIMEOUT_SECONDS):
        state.locked = False
        state.current_user_token = None
    
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
# 🛑 شاشة الانتظار
# ==========================================
if status == False:
    st.markdown("""
    <div class="library-header">
        <div class="library-title">المكتبة الرقمية</div>
        <div class="library-subtitle">نظام البحث في الكتب والمراجع</div>
    </div>
    """, unsafe_allow_html=True)
    
    time_passed = int(time.time() - state.last_activity)
    time_left = TIMEOUT_SECONDS - time_passed
    if time_left < 0: time_left = 0
    
    st.markdown("""
    <div class="waiting-container">
        <div class="waiting-title">⏸️ النظام مشغول حالياً</div>
        <div class="waiting-text">
            يستخدم أحد الباحثين النظام في الوقت الحالي.<br>
            للحفاظ على استقرار الخدمة، يُسمح بدخول مستخدم واحد فقط في كل مرة.
        </div>
        <div class="timer-display">
            {} ثانية
        </div>
        <div class="waiting-text" style="font-size: 0.95rem;">
            سيتم إتاحة النظام تلقائياً عند انتهاء المدة المحددة
        </div>
    </div>
    """.format(time_left), unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("تحديث الحالة", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    with st.expander("دخول المسؤول"):
        password_attempt = st.text_input("كلمة المرور:", type="password", key="admin_pass_locked")
        if st.button("دخول"):
            if password_attempt == st.secrets["admin_password"]:
                st.session_state.is_admin = True
                st.success("✓ تم التحقق من الهوية")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("كلمة المرور غير صحيحة")
    
    st.stop()

# ==========================================
# 👋 شاشة الترحيب
# ==========================================
elif status == "READY_TO_ENTER":
    st.markdown("""
    <div class="library-header">
        <div class="library-title">المكتبة الرقمية</div>
        <div class="library-subtitle">نظام البحث في الكتب والمراجع</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="welcome-box">
        <div class="welcome-title">مرحباً بك في المكتبة</div>
        <div class="welcome-description">
            يوفر لك هذا النظام إمكانية البحث في آلاف الكتب والمراجع العلمية والأدبية
            من مختلف المجالات المعرفية. استخدم محرك البحث للعثور على الكتاب المطلوب
            وتحميله مباشرة إلى جهازك.
        </div>
        <div style="margin-bottom: 2rem;">
            <span class="badge" style="background: #27ae60; color: white; border-color: #229954;">
                <span class="status-indicator" style="width: 8px; height: 8px; margin-left: 0.3rem;"></span>
                النظام متاح الآن
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📚 بدء استخدام المكتبة", use_container_width=True, type="primary"):
            state.locked = True
            state.current_user_token = st.session_state.user_token
            state.last_activity = time.time()
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("دخول المسؤول"):
        password_attempt = st.text_input("كلمة المرور:", type="password", key="admin_pass_open")
        if st.button("دخول"):
            if password_attempt == st.secrets["admin_password"]:
                st.session_state.is_admin = True
                st.rerun()
    
    st.stop()

# ==========================================
# ✅ التطبيق الرئيسي
# ==========================================

# الهيدر الرئيسي
st.markdown("""
<div class="library-header">
    <div class="library-title">المكتبة الرقمية</div>
    <div class="library-subtitle">نظام البحث في الكتب والمراجع</div>
</div>
""", unsafe_allow_html=True)

# شريط المعلومات العلوي
if st.session_state.is_admin:
    status_badge = '<span class="badge badge-admin">مسؤول النظام</span>'
else:
    time_left_session = TIMEOUT_SECONDS - int(time.time() - state.last_activity)
    status_badge = f'<span class="badge">الوقت المتبقي: {time_left_session} ثانية</span>'

col_info1, col_info2, col_info3 = st.columns([2, 6, 2])

with col_info1:
    st.markdown(f'<div style="padding: 0.5rem;">{status_badge}</div>', unsafe_allow_html=True)

with col_info3:
    if st.button("إنهاء الجلسة", use_container_width=True):
        if st.session_state.is_admin:
            st.session_state.is_admin = False
        else:
            state.locked = False
            state.current_user_token = None
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
            async for message in client.iter_messages(entity, search=query, limit=30):
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

# --- واجهة البحث ---
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'search_time' not in st.session_state:
    st.session_state.search_time = None

# صندوق البحث
st.markdown('<div class="search-container">', unsafe_allow_html=True)
st.markdown('<span class="search-label">البحث في فهرس المكتبة</span>', unsafe_allow_html=True)

col_search, col_btn = st.columns([6, 1])

with col_search:
    query = st.text_input(
        "بحث",
        placeholder="أدخل عنوان الكتاب، اسم المؤلف، أو الموضوع...",
        label_visibility="collapsed"
    )

with col_btn:
    search_button = st.button("بحث", use_container_width=True, type="primary")

st.markdown('</div>', unsafe_allow_html=True)

if search_button and query:
    state.last_activity = time.time()
    start_time = time.time()
    
    with st.spinner("جاري البحث في قاعدة البيانات..."):
        st.session_state.search_results = search_books_async(query)
        st.session_state.search_time = round(time.time() - start_time, 2)

# عرض النتائج
if st.session_state.search_results:
    st.markdown(f"""
    <div class="results-header">
        <div class="results-title">نتائج البحث</div>
        <div class="results-stats">
            عدد النتائج: {len(st.session_state.search_results)} • 
            وقت البحث: {st.session_state.search_time} ثانية
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    for index, item in enumerate(st.session_state.search_results, 1):
        # تجهيز الوصف
        caption_text = item['caption'].strip() if item['caption'] else "لا يوجد وصف متاح لهذا الكتاب."
        
        st.markdown(f"""
        <div class="book-item">
            <div class="book-number">النتيجة #{index}</div>
            <div class="book-main-title">{item['file_name']}</div>
            <div class="book-metadata">
                <span>📁 الحجم: {item['size'] / (1024*1024):.2f} ميجابايت</span>
            </div>
            <div class="book-description">{caption_text}</div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([3, 2, 3])
        with col2:
            btn_key = f"btn_{item['id']}"
            if st.button("تحميل الكتاب", key=btn_key, use_container_width=True):
                state.last_activity = time.time()
                
                buff, fname = download_book_to_memory(item['id'])
                if buff:
                    st.download_button(
                        label="حفظ الملف",
                        data=buff,
                        file_name=fname,
                        mime="application/octet-stream",
                        key=f"save_{item['id']}",
                        use_container_width=True
                    )
        
        st.markdown("<br>", unsafe_allow_html=True)

elif query and search_button:
    st.info("لم يتم العثور على نتائج مطابقة. حاول استخدام كلمات بحث مختلفة.")