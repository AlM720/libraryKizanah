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

# =========================
# 🎨 تصميم يشبه واجهة جوجل
# =========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Tajawal:wght@300;400;500;700&display=swap');
    
    * {
        font-family: 'Tajawal', sans-serif;
        box-sizing: border-box;
    }

    body {
        background-color: #ffffff;
    }

    h1, h2, h3 {
        font-family: 'Amiri', serif;
    }

    /* الشريط العلوي */
    .top-bar {
        width: 100%;
        padding: 0.8rem 2rem;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        direction: rtl;
    }

    .top-left, .top-right {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .top-label {
        font-size: 0.95rem;
        color: #555555;
    }

    .session-timer {
        font-weight: 600;
        color: #202124;
        font-size: 0.95rem;
        min-width: 90px;
        text-align: center;
    }

    .end-session-btn {
        padding: 0.35rem 0.8rem;
        background-color: #d93025;
        color: #ffffff;
        border-radius: 16px;
        font-size: 0.85rem;
        border: none;
    }

    .admin-link {
        font-size: 0.95rem;
        color: #1a73e8;
        cursor: pointer;
        text-decoration: none;
    }

    .admin-link:hover {
        text-decoration: underline;
    }

    /* منطقة البحث في الوسط (أسلوب جوجل) */
    .center-wrapper {
        min-height: calc(100vh - 80px);
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .search-container {
        text-align: center;
        max-width: 700px;
        width: 100%;
    }

    .search-title {
        font-size: 2.8rem;
        font-weight: 700;
        color: #202124;
        margin-bottom: 1rem;
    }

    .search-subtitle {
        font-size: 1rem;
        color: #5f6368;
        margin-bottom: 2rem;
    }

    .search-box-wrapper {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
    }

    .search-box-wrapper > div {
        flex: 1;
        max-width: 600px;
    }

    .stTextInput>div>div>input {
        border-radius: 24px !important;
        padding: 0.8rem 1.2rem !important;
        font-size: 1rem !important;
        border: 1px solid #dfe1e5 !important;
        background: #ffffff !important;
        color: #000000 !important;
    }

    .stTextInput>div>div>input:focus {
        border-color: #1a73e8 !important;
        box-shadow: 0 0 0 1px #1a73e8 !important;
    }

    .stButton>button {
        border-radius: 4px;
        border: 1px solid #f8f9fa;
        background-color: #f8f9fa;
        color: #3c4043;
        font-size: 0.9rem;
        padding: 0.45rem 1.1rem;
        cursor: pointer;
        transition: 0.2s ease;
    }

    .stButton>button:hover {
        box-shadow: 0 1px 1px rgba(0,0,0,0.1);
        border-color: #dadce0;
        background-color: #f8f9fa;
    }

    .results-header {
        margin-top: 1.2rem;
        text-align: right;
        direction: rtl;
        color: #5f6368;
        font-size: 0.9rem;
    }

    .result-card {
        border-bottom: 1px solid #e0e0e0;
        padding: 0.8rem 0;
        direction: rtl;
        text-align: right;
    }

    .result-title {
        font-size: 1rem;
        color: #1a0dab;
        margin-bottom: 0.1rem;
        font-weight: 600;
        word-wrap: break-word;
    }

    .result-meta {
        font-size: 0.8rem;
        color: #5f6368;
        margin-bottom: 0.3rem;
    }

    .result-caption {
        font-size: 0.9rem;
        color: #4d5156;
    }

    .pagination-bar {
        margin-top: 1rem;
        display: flex;
        justify-content: center;
        gap: 0.5rem;
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

if 'search_results' not in st.session_state:
    st.session_state.search_results = []

if 'search_time' not in st.session_state:
    st.session_state.search_time = None

if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

if 'session_start_time' not in st.session_state:
    st.session_state.session_start_time = None

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
        st.session_state.session_start_time = None
    
    if st.session_state.is_admin:
        return "ADMIN_ACCESS"

    if state.locked and state.current_user_token == st.session_state.user_token:
        state.last_activity = current_time 
        return "USER_ACCESS"
    
    if not state.locked:
        return "READY_TO_ENTER"
        
    return False

status = check_access()

# --- دوال الاتصال مع تيليجرام ---
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

# --- دالة تنظيف الوصف من الروابط (تبقى كما هي للاستخدام مع النتائج) ---
def clean_description(text):
    """إزالة الروابط من النص"""
    if not text:
        return "لا يوجد وصف متاح لهذا الكتاب."
    
    text = re.sub(r'https?://S+', '', text)
    text = re.sub(r'www.S+', '', text)
    text = re.sub(r't.me/S+', '', text)
    text = re.sub(r's+', ' ', text).strip()
    
    return text if text else "لا يوجد وصف متاح لهذا الكتاب."


# ==========================
# واجهة الشريط العلوي العام
# ==========================
def render_top_bar():
    remaining = 0
    if st.session_state.session_start_time is not None:
        elapsed = int(time.time() - st.session_state.session_start_time)
        remaining = max(0, TIMEOUT_SECONDS - elapsed)
    # تحويل للعرض (دقائق:ثواني)
    minutes = remaining // 60
    seconds = remaining % 60
    timer_str = f"{minutes:02d}:{seconds:02d}"
    
    col_top = st.container()
    with col_top:
        st.markdown(
            f"""
            <div class="top-bar">
                <div class="top-right">
                    <span class="top-label">مدة الجلسة المتبقية</span>
                    <span class="session-timer">{timer_str}</span>
                </div>
                <div class="top-left">
                    <a class="admin-link" href="#" onclick="return false;">دخول المشرف</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    return timer_str

# لكن لا يمكن ربط onclick بجافاسكربت من Streamlit بسهولة، لذا نضيف أزرار فعلية مخفية ضمن الشريط:
def render_top_controls():
    top_cols = st.columns([3, 1, 1])
    with top_cols[1]:
        # زر إنهاء الجلسة
        end_session = st.button("إنهاء الجلسة", key="end_session_top")
    with top_cols[2]:
        admin_btn = st.button("دخول المشرف", key="admin_top")
    return end_session, admin_btn

# ==========================
# منطق الواجهة حسب حالة الدخول
# ==========================
def show_admin_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="text-align:center; direction:rtl;">
            <h2>دخول المشرف</h2>
            <p>أدخل كلمة المرور للدخول إلى وضع المشرف.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    password = st.text_input("كلمة مرور المشرف", type="password", key="admin_pass_input")
    if st.button("تأكيد الدخول", key="admin_login_btn"):
        if password == st.secrets["admin_password"]:
            st.session_state.is_admin = True
            st.session_state.admin_mode = True
            st.success("تم تسجيل الدخول كمشرف.")
            st.rerun()
        else:
            st.error("كلمة المرور غير صحيحة.")

def show_google_like_search():
    st.markdown("<br>", unsafe_allow_html=True)
    render_top_bar()
    end_session, admin_btn = render_top_controls()
    
    # أزرار الشريط
    if end_session:
        state.locked = False
        state.current_user_token = None
        st.session_state.session_start_time = None
        clear_session_data()
        st.success("تم إنهاء الجلسة الحالية.")
        st.experimental_rerun()
    if admin_btn:
        st.session_state.admin_mode = True
        st.experimental_rerun()

    # منطقة البحث في الوسط
    st.markdown("<div class='center-wrapper'><div class='search-container'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="search-title">المكتبة الرقمية</div>
        <div class="search-subtitle">
            محرك بحث عن الكتب والمراجع من قناة تيليجرام.
        </div>
        """,
        unsafe_allow_html=True
    )

    # مربع البحث
    col_search = st.container()
    with col_search:
        st.markdown("<div class='search-box-wrapper'>", unsafe_allow_html=True)
        query = st.text_input("ابحث عن كتاب", label_visibility="collapsed", key="main_search_input")
        st.markdown("</div>", unsafe_allow_html=True)

        btn_cols = st.columns([1, 1, 1])
        with btn_cols[1]:
            search_clicked = st.button("بحث عن الكتب", key="search_books_btn")

    st.markdown("</div></div>", unsafe_allow_html=True)

    # تنفيذ البحث
    if search_clicked and query.strip():
        start_time = time.time()
        st.session_state.search_results = search_books_async(query.strip())
        st.session_state.search_time = time.time() - start_time
        st.session_state.current_page = 0
        st.experimental_rerun()

    # عرض النتائج إن وجدت
    if st.session_state.search_results:
        total_results = len(st.session_state.search_results)
        page = st.session_state.current_page
        start_idx = page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_results = st.session_state.search_results[start_idx:end_idx]

        st.markdown(
            f"<div class='results-header'>حوالي {total_results} نتيجة (في {st.session_state.search_time:.2f} ثانية)</div>",
            unsafe_allow_html=True
        )

        for result in page_results:
            with st.container():
                st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='result-title'>{result['file_name']}</div>",
                    unsafe_allow_html=True
                )
                size_mb = result['size'] / (1024 * 1024)
                st.markdown(
                    f"<div class='result-meta'>الحجم: {size_mb:.2f} م.ب - التاريخ: {result['date'].strftime('%Y-%m-%d')}</div>",
                    unsafe_allow_html=True
                )
                caption = clean_description(result['caption'])
                st.markdown(
                    f"<div class='result-caption'>{caption}</div>",
                    unsafe_allow_html=True
                )

                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button("تحميل الكتاب", key=f"download_{result['id']}"):
                        buffer, file_name = download_book_to_memory(result['id'])
                        if buffer:
                            st.download_button(
                                label="اضغط هنا لحفظ الملف",
                                data=buffer,
                                file_name=file_name,
                                mime="application/pdf",
                                key=f"save_{result['id']}"
                            )
                with c2:
                    if st.button("معاينة الصفحة الأولى", key=f"preview_{result['id']}"):
                        img = get_first_page_preview(result['id'])
                        if img:
                            st.image(img, caption="الصفحة الأولى")

                st.markdown("</div>", unsafe_allow_html=True)

        # شريط الصفحات
        total_pages = (total_results - 1) // ITEMS_PER_PAGE + 1
        if total_pages > 1:
            st.markdown("<div class='pagination-bar'>", unsafe_allow_html=True)
            col_prev, col_page, col_next = st.columns([1, 2, 1])
            with col_prev:
                if st.button("السابق", disabled=(page == 0)):
                    st.session_state.current_page -= 1
                    st.experimental_rerun()
            with col_page:
                st.markdown(
                    f"<div style='text-align:center; direction:rtl;'>صفحة {page+1} من {total_pages}</div>",
                    unsafe_allow_html=True
                )
            with col_next:
                if st.button("التالي", disabled=(page >= total_pages - 1)):
                    st.session_state.current_page += 1
                    st.experimental_rerun()
            st.markdown("</div>", unsafe_allow_html=True)


# ==========================
# تدفق التطبيق الأساسي
# ==========================

if status == "ADMIN_PANEL":
    # في هذا الوضع يمكن لاحقاً إضافة واجهة خاصة بالمشرف إن رغبت
    render_top_bar()
    end_session, _ = render_top_controls()
    if end_session:
        state.locked = False
        state.current_user_token = None
        st.session_state.session_start_time = None
        st.session_state.admin_mode = False
        clear_session_data()
        st.success("تم إنهاء الجلسة الحالية.")
        st.experimental_rerun()
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("أنت الآن في وضع المشرف. (واجهة إدارة مفصلة يمكن إضافتها هنا لاحقاً).")

elif status == "ADMIN_ACCESS":
    render_top_bar()
    end_session, _ = render_top_controls()
    if end_session:
        state.locked = False
        state.current_user_token = None
        st.session_state.session_start_time = None
        st.session_state.is_admin = False
        clear_session_data()
        st.success("تم إنهاء الجلسة الحالية.")
        st.experimental_rerun()
    show_google_like_search()

elif status == "USER_ACCESS":
    # جلسة مستخدم قائمة
    if st.session_state.session_start_time is None:
        st.session_state.session_start_time = time.time()
    show_google_like_search()

elif status == "READY_TO_ENTER":
    # لا توجد جلسة حالياً: شاشة دخول تشبه صفحة جوجل الأولى
    render_top_bar()
    end_session, admin_btn = render_top_controls()
    if end_session:
        # لا يوجد شيء لإنهائه فعلياً لكن نبقي المنطق
        state.locked = False
        state.current_user_token = None
        st.session_state.session_start_time = None
        clear_session_data()
        st.experimental_rerun()
    if admin_btn:
        show_admin_login()
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='center-wrapper'><div class='search-container'>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="search-title">المكتبة الرقمية</div>
            <div class="search-subtitle">
                نظام يسمح بدخول جلسة واحدة فقط في كل مرة. اضغط على الزر لبدء جلستك.
            </div>
            """,
            unsafe_allow_html=True
        )
        col_center = st.columns([1, 1, 1])
        with col_center[1]:
            if st.button("بدء استخدام المكتبة", key="start_session_btn"):
                state.locked = True
                state.current_user_token = st.session_state.user_token
                state.last_activity = time.time()
                st.session_state.session_start_time = time.time()
                st.experimental_rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)

else:
    # حالة: النظام مقفول ومستخدم آخر يحاول الدخول
    render_top_bar()
    end_session, admin_btn = render_top_controls()
    if end_session:
        # لا يُسمح للمستخدم العادي بإغلاق جلسة مستخدم آخر
        st.warning("لا يمكنك إنهاء جلسة مستخدم آخر. اطلب من المشرف التدخل.")
    if admin_btn:
        show_admin_login()
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.warning("هناك جلسة مستخدم أخرى قيد العمل حالياً. الرجاء المحاولة لاحقاً.")