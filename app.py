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
    page_title="باحث الكتب",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تصميم CSS مخصص ---
st.markdown("""
<style>
    /* الخط العربي */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Cairo', sans-serif;
    }
    
    /* إخفاء عناصر streamlit الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* الخلفية الرئيسية */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* البطاقات */
    .main-card {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    /* عنوان التطبيق */
    .app-title {
        text-align: center;
        color: white;
        font-size: 3rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .app-subtitle {
        text-align: center;
        color: rgba(255,255,255,0.9);
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    
    /* بطاقة الكتاب */
    .book-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border-left: 5px solid #667eea;
    }
    
    .book-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    }
    
    .book-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 0.5rem;
    }
    
    .book-info {
        color: #718096;
        font-size: 0.9rem;
    }
    
    /* الأزرار */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    /* شريط البحث */
    .stTextInput>div>div>input {
        border-radius: 15px;
        border: 2px solid #e2e8f0;
        padding: 0.75rem 1rem;
        font-size: 1.1rem;
    }
    
    /* حالة الانتظار */
    .waiting-box {
        background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%);
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        color: #2d3748;
    }
    
    .waiting-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    
    /* شارة الحالة */
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .status-online {
        background: #48bb78;
        color: white;
    }
    
    .status-busy {
        background: #f56565;
        color: white;
    }
    
    /* عداد الوقت */
    .timer-box {
        background: rgba(255,255,255,0.2);
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        color: white;
        text-align: center;
    }
    
    .timer-number {
        font-size: 2rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# --- ⚙️ إعدادات النظام ---
TIMEOUT_SECONDS = 180

# التأكد من وجود البيانات
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
    st.markdown('<div class="app-title">📖 باحث الكتب</div>', unsafe_allow_html=True)
    
    time_passed = int(time.time() - state.last_activity)
    time_left = TIMEOUT_SECONDS - time_passed
    if time_left < 0: time_left = 0
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"""
        <div class="waiting-box">
            <div class="waiting-icon">⏳</div>
            <h2>المكتبة مشغولة حالياً</h2>
            <p style="font-size: 1.1rem; margin: 1rem 0;">
                يوجد مستخدم آخر يستخدم النظام الآن
            </p>
            <div class="timer-box">
                <div>الوقت المتبقي للإتاحة التلقائية</div>
                <div class="timer-number">{time_left}</div>
                <div>ثانية</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🔄 تحديث الحالة", use_container_width=True, type="primary"):
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.expander("🔐 دخول المدير"):
            password_attempt = st.text_input("كلمة المرور:", type="password", key="admin_pass_locked")
            if st.button("دخول", use_container_width=True):
                if password_attempt == st.secrets["admin_password"]:
                    st.session_state.is_admin = True
                    st.success("✅ تم التحقق بنجاح")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ كلمة المرور خاطئة")
    
    st.stop()

# ==========================================
# 👋 شاشة الترحيب
# ==========================================
elif status == "READY_TO_ENTER":
    st.markdown('<div class="app-title">📖 باحث الكتب</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">اكتشف عالم الكتب والمعرفة</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="main-card" style="text-align: center;">
            <h2 style="color: #667eea; margin-bottom: 1rem;">مرحباً بك في المكتبة الرقمية</h2>
            <p style="font-size: 1.1rem; color: #718096; margin-bottom: 2rem;">
                ابحث عن آلاف الكتب في جميع المجالات
            </p>
            <span class="status-badge status-online">⚡ النظام متاح الآن</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 ابدأ البحث الآن", use_container_width=True, type="primary"):
            state.locked = True
            state.current_user_token = st.session_state.user_token
            state.last_activity = time.time()
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.expander("🔐 تسجيل دخول المدير"):
            password_attempt = st.text_input("كلمة المرور:", type="password", key="admin_pass_open")
            if st.button("دخول", use_container_width=True):
                if password_attempt == st.secrets["admin_password"]:
                    st.session_state.is_admin = True
                    st.rerun()
    
    st.stop()

# ==========================================
# ✅ التطبيق الرئيسي
# ==========================================

# الشريط العلوي
col_header1, col_header2, col_header3 = st.columns([2, 6, 2])

with col_header1:
    st.markdown('<div class="app-title" style="font-size: 2rem; margin: 0;">📖 باحث الكتب</div>', unsafe_allow_html=True)

with col_header3:
    if st.session_state.is_admin:
        st.markdown('<span class="status-badge" style="background: #9f7aea; color: white;">👑 مدير</span>', unsafe_allow_html=True)
    else:
        time_left_session = TIMEOUT_SECONDS - int(time.time() - state.last_activity)
        st.markdown(f'<span class="status-badge status-online">⏱️ {time_left_session}ث</span>', unsafe_allow_html=True)
    
    if st.button("🚪 خروج", use_container_width=True):
        if st.session_state.is_admin:
            st.session_state.is_admin = False
        else:
            state.locked = False
            state.current_user_token = None
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# تحذير للمدير
if status == "ADMIN_ACCESS" and state.locked and state.current_user_token != st.session_state.user_token:
    st.warning("⚠️ تنبيه: يوجد مستخدم آخر نشط حالياً. استخدامكما المتزامن قد يسبب مشاكل.")

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
            st.error(f"❌ خطأ في الاتصال: {e}")
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
                col_prog.text(f"📥 جاري التحميل: {file_name}")
                
                def callback(current, total):
                    progress_bar.progress(current / total)
                
                await client.download_media(message, buffer, progress_callback=callback)
                buffer.seek(0)
            else:
                st.error("❌ الملف غير موجود")
        except Exception as e:
            st.error(f"❌ فشل التحميل: {e}")
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

# بطاقة البحث
col1, col2, col3 = st.columns([1, 6, 1])

with col2:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    col_search, col_btn = st.columns([5, 1])
    
    with col_search:
        query = st.text_input(
            "بحث",
            placeholder="ابحث عن كتاب، مؤلف، أو موضوع...",
            label_visibility="collapsed"
        )
    
    with col_btn:
        search_button = st.button("🔍", use_container_width=True, type="primary")
    
    if search_button and query:
        state.last_activity = time.time()
        start_time = time.time()
        
        with st.spinner("🔍 جاري البحث في المكتبة..."):
            st.session_state.search_results = search_books_async(query)
            st.session_state.search_time = round(time.time() - start_time, 2)
    
    st.markdown('</div>', unsafe_allow_html=True)

# عرض النتائج
if st.session_state.search_results:
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col2:
        st.markdown(f"""
        <div class="main-card">
            <h3 style="color: #667eea;">📚 نتائج البحث</h3>
            <p style="color: #718096;">
                تم العثور على <strong>{len(st.session_state.search_results)}</strong> نتيجة
                في <strong>{st.session_state.search_time}</strong> ثانية
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        for item in st.session_state.search_results:
            st.markdown(f"""
            <div class="book-card">
                <div class="book-title">📖 {item['file_name']}</div>
                <div class="book-info">📦 الحجم: {item['size'] / (1024*1024):.1f} ميجابايت</div>
            </div>
            """, unsafe_allow_html=True)
            
            col_desc, col_down = st.columns([3, 1])
            
            with col_desc:
                if item['caption']:
                    with st.expander("📄 الوصف"):
                        st.text(item['caption'])
            
            with col_down:
                btn_key = f"btn_{item['id']}"
                if st.button("⬇️ تحميل", key=btn_key, use_container_width=True):
                    state.last_activity = time.time()
                    
                    buff, fname = download_book_to_memory(item['id'])
                    if buff:
                        st.download_button(
                            label="💾 حفظ الملف",
                            data=buff,
                            file_name=fname,
                            mime="application/octet-stream",
                            key=f"save_{item['id']}",
                            use_container_width=True
                        )

elif query and search_button:
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.info("🔍 لم يتم العثور على نتائج جرب كلمات بحث أخرى.")