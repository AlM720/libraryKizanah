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
    
    /* بطاقة الكتاب */
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
        font-size: 1rem;
        margin-bottom: 1rem;
        padding: 0.7rem 0;
        border-top: 1px solid #ecf0f1;
        border-bottom: 1px solid #ecf0f1;
        font-weight: 500;
    }
    
    .book-metadata span {
        margin-left: 1.5rem;
    }
    
    .book-description {
        color: #5a6c7d;
        font-size: 1rem;
        line-height: 1.8;
        margin-bottom: 1.5rem;
        text-align: justify;
    }
    
    .action-buttons-area {
        background: #f8f9fa;
        border-top: 2px solid #e9ecef;
        padding: 1.5rem;
        margin-top: 1rem;
        border-radius: 4px;
    }
    
    /* الأزرار */
    .stButton>button {
        background: #34495e !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 0.85rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        transition: all 0.3s ease !important;
        letter-spacing: 0.3px !important;
    }
    
    .stButton>button:hover {
        background: #2c3e50 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.25) !important;
        transform: translateY(-2px) !important;
    }
    
    .stButton>button:active {
        transform: translateY(0) !important;
    }
    
    div[data-testid="column"]:has(button) {
        padding: 0.3rem;
    }
    
    .stDownloadButton>button {
        background: #27ae60 !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        padding: 0.8rem 1.5rem !important;
    }
    
    .stDownloadButton>button:hover {
        background: #229954 !important;
        box-shadow: 0 4px 8px rgba(39, 174, 96, 0.3) !important;
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
    
    .admin-control-box {
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 4px;
        padding: 1.5rem;
        margin: 1.5rem 0;
    }
    
    /* لوحة التحكم */
    .admin-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .duplicate-card {
        background: white;
        border: 2px solid #e74c3c;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .file-info {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        border-left: 4px solid #3498db;
    }
    
    .warning-box {
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .success-box {
        background: #d4edda;
        border: 2px solid #28a745;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- ⚙️ إعدادات النظام ---
TIMEOUT_SECONDS = 180
ITEMS_PER_PAGE = 5

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

if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False

if 'duplicate_groups' not in st.session_state:
    st.session_state.duplicate_groups = []

if 'scan_completed' not in st.session_state:
    st.session_state.scan_completed = False

if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

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
    
    # وضع لوحة التحكم يمنع الجميع
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

# دوال لوحة التحكم
async def scan_for_duplicates():
    """مسح القناة والبحث عن الملفات المكررة"""
    client = await get_client()
    files_by_size = defaultdict(list)
    
    try:
        entity = await client.get_entity(channel_id)
        
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
        
        potential_duplicates = []
        for size, files in files_by_size.items():
            if len(files) > 1:
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

# ==========================================
# لوحة التحكم
# ==========================================
if st.session_state.admin_mode:
    st.markdown("""
    <div class="admin-header">
        <div style="font-size: 2.5rem; font-weight: 700;">🗂️ إدارة الملفات المكررة</div>
        <p style="font-size: 1.1rem; margin-top: 0.5rem;">نظام الكشف والحذف الذكي</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_info1, col_info2 = st.columns([3, 1])
    
    with col_info1:
        st.info("🔒 **الجلسات الأخرى متوقفة** - أنت الوحيد المسموح له بالدخول حالياً")
    
    with col_info2:
        if st.button("🚪 خروج", use_container_width=True):
            st.session_state.admin_mode = False
            st.session_state.duplicate_groups = []
            st.session_state.scan_completed = False
            st.session_state.current_page = 0
            st.rerun()
    
    st.markdown("---")
    
    if not st.session_state.scan_completed:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div class="warning-box" style="text-align: center;">
                <h3 style="color: #856404;">🔍 ابدأ عملية المسح</h3>
                <p>سيتم فحص جميع الملفات في القناة للبحث عن المكررات</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔍 بدء المسح الآن", use_container_width=True, type="primary"):
                with st.spinner("⏳ جاري مسح القناة... قد يستغرق بعض الوقت"):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    duplicates = loop.run_until_complete(scan_for_duplicates())
                    loop.close()
                    
                    st.session_state.duplicate_groups = duplicates
                    st.session_state.scan_completed = True
                    st.session_state.current_page = 0
                    st.rerun()
    else:
        if len(st.session_state.duplicate_groups) == 0:
            st.markdown("""
            <div class="success-box" style="text-align: center;">
                <h2 style="color: #155724;">✅ رائع!</h2>
                <p style="font-size: 1.2rem;">لا توجد ملفات مكررة في القناة</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔄 إعادة المسح", use_container_width=True):
                st.session_state.scan_completed = False
                st.session_state.duplicate_groups = []
                st.session_state.current_page = 0
                st.rerun()
        else:
            st.success(f"✓ تم العثور على **{len(st.session_state.duplicate_groups)}** مجموعة من الملفات المحتملة المكررة")
            
            if st.button("🔄 إعادة المسح", use_container_width=True):
                st.session_state.scan_completed = False
                st.session_state.duplicate_groups = []
                st.session_state.current_page = 0
                st.rerun()
            
            st.markdown("---")
            
            # حساب عدد الصفحات
            total_groups = len(st.session_state.duplicate_groups)
            total_pages = (total_groups + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            current_page = st.session_state.current_page
            
            # عرض معلومات الصفحة
            start_idx = current_page * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, total_groups)
            
            st.info(f"📄 الصفحة {current_page + 1} من {total_pages} | عرض المجموعات {start_idx + 1} - {end_idx} من {total_groups}")
            
            # أزرار التنقل العلوية
            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            
            with col_nav1:
                if current_page > 0:
                    if st.button("⏮️ السابق", use_container_width=True):
                        st.session_state.current_page -= 1
                        st.rerun()
            
            with col_nav3:
                if current_page < total_pages - 1:
                    if st.button("التالي ⏭️", use_container_width=True, type="primary"):
                        st.session_state.current_page += 1
                        st.rerun()
            
            st.markdown("---")
            
            # عرض المجموعات الحالية فقط
            current_groups = st.session_state.duplicate_groups[start_idx:end_idx]
            
            for idx, group in enumerate(current_groups, start=start_idx + 1):
                st.markdown(f"""
                <div class="duplicate-card">
                    <h3 style="color: #c0392b;">🔴 مجموعة مكررة #{idx}</h3>
                    <p><strong>الحجم المشترك:</strong> {group[0]['size'] / (1024*1024):.2f} ميجابايت</p>
                    <p><strong>عدد الملفات:</strong> {len(group)} ملف</p>
                </div>
                """, unsafe_allow_html=True)
                
                for file_idx, file in enumerate(group, 1):
                    with st.expander(f"📄 الملف {file_idx}: {file['name']}", expanded=False):
                        st.markdown(f"""
                        <div class="file-info">
                            <p><strong>الاسم:</strong> {file['name']}</p>
                            <p><strong>الحجم:</strong> {file['size'] / (1024*1024):.2f} ميجابايت</p>
                            <p><strong>التاريخ:</strong> {file['date'].strftime('%Y-%m-%d %H:%M')}</p>
                            <p><strong>الوصف:</strong> {file['caption'][:100] if file['caption'] else 'لا يوجد'}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button(f"📊 فحص عدد الصفحات", key=f"check_pages_{file['id']}"):
                                with st.spinner("جاري الفحص..."):
                                    pages = get_pdf_page_count(file['id'])
                                    
                                    if pages:
                                        st.success(f"📖 عدد الصفحات: {pages}")
                                    else:
                                        st.warning("لم نتمكن من حساب عدد الصفحات (قد لا يكون PDF)")
                        
                        with col2:
                            delete_key = f"delete_{file['id']}"
                            if st.button(f"🗑️ حذف هذا الملف", key=delete_key, type="primary"):
                                st.warning("⚠️ تأكيد الحذف")
                                confirm_key = f"confirm_{file['id']}"
                                if st.button(f"✓ نعم، احذف نهائياً", key=confirm_key):
                                    with st.spinner("جاري الحذف..."):
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        success = loop.run_until_complete(delete_file(file['id']))
                                        loop.close()
                                        
                                        if success:
                                            st.success("✓ تم الحذف بنجاح!")
                                            
                                            # حذف الملف من القائمة مباشرة دون إعادة المسح
                                            for i, g in enumerate(st.session_state.duplicate_groups):
                                                # البحث عن المجموعة التي تحتوي هذا الملف
                                                for j, f in enumerate(g):
                                                    if f['id'] == file['id']:
                                                        # حذف الملف من المجموعة
                                                        del st.session_state.duplicate_groups[i][j]
                                                        
                                                        # إذا أصبحت المجموعة تحتوي على ملف واحد فقط، احذف المجموعة كلها
                                                        if len(st.session_state.duplicate_groups[i]) <= 1:
                                                            del st.session_state.duplicate_groups[i]
                                                        
                                                        break
                                            
                                            # إذا انتهت كل المجموعات، ارجع للصفحة الأولى
                                            if len(st.session_state.duplicate_groups) == 0:
                                                st.session_state.current_page = 0
                                            # إذا الصفحة الحالية أصبحت فارغة، ارجع للصفحة السابقة
                                            elif st.session_state.current_page * ITEMS_PER_PAGE >= len(st.session_state.duplicate_groups):
                                                st.session_state.current_page = max(0, st.session_state.current_page - 1)
                                            
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("فشل الحذف")
                
                st.markdown("<br>", unsafe_allow_html=True)
            
            # أزرار التنقل السفلية
            st.markdown("---")
            col_nav4, col_nav5, col_nav6 = st.columns([1, 2, 1])
            
            with col_nav4:
                if current_page > 0:
                    if st.button("⏮️ السابق", use_container_width=True, key="prev_bottom"):
                        st.session_state.current_page -= 1
                        st.rerun()
            
            with col_nav6:
                if current_page < total_pages - 1:
                    if st.button("التالي ⏭️", use_container_width=True, type="primary", key="next_bottom"):
                        st.session_state.current_page += 1
                        st.rerun()
    
    st.stop()

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
    
    with st.expander("🔐 لوحة تحكم المشرف"):
        st.markdown('<div class="admin-control-box">', unsafe_allow_html=True)
        st.markdown("**إنهاء الجلسة الحالية أو الدخول للوحة التحكم**")
        
        supervisor_key = st.text_input("مفتاح المشرف:", type="password", key="supervisor_key_waiting")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("إنهاء الجلسة الحالية", use_container_width=True):
                if supervisor_key == st.secrets["key"]:
                    state.locked = False
                    state.current_user_token = None
                    clear_session_data()
                    st.success("✓ تم إنهاء الجلسة بنجاح")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ مفتاح المشرف غير صحيح")
        
        with col_btn2:
            if st.button("لوحة إدارة المكررات", use_container_width=True, type="primary"):
                if supervisor_key == st.secrets["key"]:
                    st.session_state.admin_mode = True
                    state.locked = False
                    state.current_user_token = None
                    clear_session_data()
                    st.rerun()
                else:
                    st.error("❌ مفتاح المشرف غير صحيح")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
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
        if st.button("بدء استخدام المكتبة", use_container_width=True, type="primary"):
            state.locked = True
            state.current_user_token = st.session_state.user_token
            state.last_activity = time.time()
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("🔐 لوحة تحكم المشرف"):
        st.markdown('<div class="admin-control-box">', unsafe_allow_html=True)
        st.markdown("**الدخول للوحة إدارة المكررات**")
        
        supervisor_key = st.text_input("مفتاح المشرف:", type="password", key="supervisor_key_welcome")
        
        if st.button("دخول لوحة التحكم", use_container_width=True, type="primary"):
            if supervisor_key == st.secrets["key"]:
                st.session_state.admin_mode = True
                st.rerun()
            else:
                st.error("❌ مفتاح المشرف غير صحيح")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
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

st.markdown("""
<div class="library-header">
    <div class="library-title">المكتبة الرقمية</div>
    <div class="library-subtitle">نظام البحث في الكتب والمراجع</div>
</div>
""", unsafe_allow_html=True)

if st.session_state.is_admin:
    status_badge = '<span class="badge badge-admin">مسؤول النظام</span>'
else:
    time_left_session = TIMEOUT_SECONDS - int(time.time() - state.last_activity)
    status_badge = f'<span class="badge">الوقت المتبقي: {time_left_session} ثانية</span>'

col_info1, col_info2, col_info3 = st.columns([2, 4, 2])

with col_info1:
    st.markdown(f'<div style="padding: 0.5rem;">{status_badge}</div>', unsafe_allow_html=True)

with col_info2:
    if st.session_state.is_admin:
        if st.button("🗂️ لوحة إدارة المكررات", use_container_width=True):
            st.session_state.admin_mode = True
            st.rerun()

with col_info3:
    if st.button("إنهاء الجلسة", use_container_width=True):
        if st.session_state.is_admin:
            st.session_state.is_admin = False
        else:
            state.locked = False
            state.current_user_token = None
        clear_session_data()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

if status == "ADMIN_ACCESS" and state.locked and state.current_user_token != st.session_state.user_token:
    st.warning("⚠️ تنبيه: يوجد مستخدم نشط آخر. الاستخدام المتزامن قد يسبب مشاكل في النظام.")
    st.markdown("<br>", unsafe_allow_html=True)

if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'search_time' not in st.session_state:
    st.session_state.search_time = None

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
        caption_text = item['caption'].strip() if item['caption'] else "لا يوجد وصف متاح لهذا الكتاب."
        
        st.markdown(f"""
        <div class="book-item">
            <div class="book-number">النتيجة #{index}</div>
            <div class="book-main-title">{item['file_name']}</div>
            <div class="book-metadata">
                <span>الحجم: {item['size'] / (1024*1024):.2f} ميجابايت</span>
            </div>
            <div class="book-description">{caption_text}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="action-buttons-area">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            pages_btn_key = f"pages_{item['id']}"
            if st.button("عدد الصفحات", key=pages_btn_key, use_container_width=True):
                state.last_activity = time.time()
                
                if item['file_name'].lower().endswith('.pdf'):
                    with st.spinner("جاري حساب عدد الصفحات..."):
                        page_count = get_pdf_page_count(item['id'])
                        if page_count:
                            st.success(f"✓ عدد الصفحات: {page_count} صفحة")
                        else:
                            st.warning("لم نتمكن من حساب عدد الصفحات")
                else:
                    st.info("هذه الميزة متاحة فقط لملفات PDF")
        
        with col2:
            preview_btn_key = f"preview_{item['id']}"
            if st.button("معاينة الكتاب", key=preview_btn_key, use_container_width=True):
                state.last_activity = time.time()
                
                if item['file_name'].lower().endswith('.pdf'):
                    with st.spinner("جاري تحضير المعاينة..."):
                        first_page = get_first_page_preview(item['id'])
                        if first_page:
                            st.image(first_page, caption="الصفحة الأولى من الكتاب", use_container_width=True)
                        else:
                            st.warning("لم نتمكن من إنشاء المعاينة")
                else:
                    st.info("المعاينة متاحة فقط لملفات PDF")
        
        with col3:
            btn_key = f"btn_{item['id']}"
            if st.button("تحميل الآن", key=btn_key, use_container_width=True, type="primary"):
                state.last_activity = time.time()
                
                buff, fname = download_book_to_memory(item['id'])
                if buff:
                    st.download_button(
                        label="حفظ على جهازك",
                        data=buff,
                        file_name=fname,
                        mime="application/octet-stream",
                        key=f"save_{item['id']}",
                        use_container_width=True
                    )
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

elif query and search_button:
    st.info("لم يتم العثور على نتائج مطابقة. حاول استخدام كلمات بحث مختلفة.")