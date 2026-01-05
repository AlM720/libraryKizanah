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

    /* تحسين التفاعل مع الأزرار */
    .stButton>button {
        background-color: #4CAF50; /* لون أخضر */
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        transition: all 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #45a049; /* تغير اللون عند التحويم */
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        transform: scale(1.05);
    }
    .stButton>button:active {
        background-color: #388E3C; /* تغير اللون عند الضغط */
    }

    /* إضافة تأثيرات على الحقول */
    .stTextInput>div>div>input {
        border: 2px solid #7f8c8d !important;
        border-radius: 4px !important;
        padding: 0.9rem 1.2rem !important;
        font-size: 1.2rem !important;
        background: white !important;
        color: #000000 !important;
        font-weight: 500 !important;
    }

    .stTextInput>div>div>input::placeholder {
        color: #95a5a6 !important;
        opacity: 0.7 !important;
    }

    .stTextInput>div>div>input:focus {
        border-color: #2c3e50 !important;
        background: white !important;
        box-shadow: 0 0 0 3px rgba(44, 62, 80, 0.1) !important;
        color: #000000 !important;
    }

    /* إضافة تلميحات للمساعدة في التفاعل */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: pointer;
    }

    .tooltip .tooltiptext {
        visibility: hidden;
        width: 120px;
        background-color: #6c757d;
        color: #fff;
        text-align: center;
        border-radius: 5px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%; /* مكان التلميح */
        left: 50%;
        margin-left: -60px;
        opacity: 0;
        transition: opacity 0.3s;
    }

    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    
    /* تحسين التنسيق العام */
    .library-header {
        background: linear-gradient(to bottom, #2c3e50 0%, #34495e 100%);
        padding: 2rem 0;
        margin-bottom: 2rem;
        border-bottom: 3px solid #95a5a6;
    }

    .library-title {
        color: #ecf0f1;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin: 0;
        letter-spacing: 1px;
    }

    .library-subtitle {
        color: #bdc3c7;
        text-align: center;
        font-size: 1.2rem;
        margin-top: 0.5rem;
        font-weight: 300;
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

if 'duplicate_groups' not in st.session_state:
    st.session_state.duplicate_groups = []

if 'scan_completed' not in st.session_state:
    st.session_state.scan_completed = False

if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

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

# دوال لوحة التحكم
def clean_description(text):
    """إزالة الروابط من النص"""
    if not text:
        return "لا يوجد وصف متاح لهذا الكتاب."
    
    # إزالة الروابط HTTP/HTTPS
    text = re.sub(r'https?://\S+', '', text)
    # إزالة الروابط www
    text = re.sub(r'www\.\S+', '', text)
    # إزالة الروابط t.me
    text = re.sub(r't\.me/\S+', '', text)
    # إزالة مسافات زائدة
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text if text else "لا يوجد وصف متاح لهذا الكتاب."

async def scan_for_duplicates():
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

def has_sequential_numbers(name1, name2):
    """التحقق من وجود أرقام متسلسلة في الأسماء"""
    numbers1 = re.findall(r'\d+', name1)
    numbers2 = re.findall(r'\d+', name2)
    
    if numbers1 and numbers2:
        for n1 in numbers1:
            for n2 in numbers2:
                if abs(int(n1) - int(n2)) == 1:
                    return True
    
    patterns = [
        r'(جزء|الجزء|part|vol|volume)\s*\d+',
        r'\d+\s*(جزء|الجزء|part|vol|volume)',
    ]
    
    for pattern in patterns:
        if re.search(pattern, name1, re.IGNORECASE) and re.search(pattern, name2, re.IGNORECASE):
            return True
    
    return False

def are_names_similar(name1, name2):
    """مقارنة الأسماء لمعرفة التشابه"""
    name1_clean = re.sub(r'\.(pdf|epub|rar|zip)$', '', name1.lower())
    name2_clean = re.sub(r'\.(pdf|epub|rar|zip)$', '', name2.lower())
    
    name1_no_nums = re.sub(r'\d+', '', name1_clean)
    name2_no_nums = re.sub(r'\d+', '', name2_clean)
    
    name1_no_nums = re.sub(r'[^\w\s]', '', name1_no_nums).strip()
    name2_no_nums = re.sub(r'[^\w\s]', '', name2_no_nums).strip()
    
    if name1_no_nums == name2_no_nums and name1_no_nums:
        return True
    
    words1 = set(name1_no_nums.split())
    words2 = set(name2_no_nums.split())
    
    if words1 and words2:
        common_words = words1.intersection(words2)
        similarity = len(common_words) / max(len(words1), len(words2))
        return similarity >= 0.7
    
    return False

def classify_duplicate_group(group):
    """تصنيف المجموعة المكررة: تلقائي أم يحتاج تأكيد"""
    if len(group) < 2:
        return "single", []
    
    names = [f['name'] for f in group]
    
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if has_sequential_numbers(names[i], names[j]):
                return "manual", group
    
    all_similar = True
    for i in range(len(names) - 1):
        if not are_names_similar(names[i], names[i + 1]):
            all_similar = False
            break
    
    if all_similar:
        sorted_group = sorted(group, key=lambda x: x['date'], reverse=True)
        keep_file = sorted_group[0]
        delete_files = sorted_group[1:]
        return "auto", delete_files
    
    return "manual", group

async def auto_delete_duplicates(files_to_delete):
    """حذف الملفات المكررة تلقائياً"""
    deleted_count = 0
    failed_count = 0
    
    for file in files_to_delete:
        success = await delete_file(file['id'])
        if success:
            deleted_count += 1
        else:
            failed_count += 1
    
    return deleted_count, failed_count

async def delete_file(message_id):
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
                with st.spinner("⏳ جاري مسح القناة..."):
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
            # تصنيف المجموعات
            auto_delete_groups = []
            manual_groups = []
            
            for group in st.session_state.duplicate_groups:
                classification, data = classify_duplicate_group(group)
                if classification == "auto":
                    auto_delete_groups.append(data)
                elif classification == "manual":
                    manual_groups.append(group)
            
            total_auto_files = sum(len(g) for g in auto_delete_groups)
            
            st.success(f"✓ تم العثور على **{len(st.session_state.duplicate_groups)}** مجموعة من الملفات المكررة")
            
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.info(f"🤖 **{total_auto_files}** ملف يمكن حذفه تلقائياً")
            with col_stat2:
                st.warning(f"👤 **{len(manual_groups)}** مجموعة تحتاج مراجعة يدوية")
            
            if auto_delete_groups:
                st.markdown("---")
                st.markdown("### 🤖 الحذف التلقائي الذكي")
                st.write("تم اكتشاف ملفات مكررة بنفس الاسم والحجم (بدون أرقام متسلسلة). يمكن حذفها تلقائياً وإبقاء أحدث نسخة.")
                
                col_auto1, col_auto2, col_auto3 = st.columns([1, 1, 1])
                with col_auto2:
                    if st.button(f"🗑️ حذف {total_auto_files} ملف تلقائياً", use_container_width=True, type="primary"):
                        with st.spinner("جاري الحذف التلقائي..."):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            all_files_to_delete = [f for group in auto_delete_groups for f in group]
                            deleted, failed = loop.run_until_complete(auto_delete_duplicates(all_files_to_delete))
                            
                            loop.close()
                            
                            if deleted > 0:
                                st.success(f"✓ تم حذف {deleted} ملف بنجاح!")
                                if failed > 0:
                                    st.warning(f"⚠️ فشل حذف {failed} ملف")
                                
                                st.session_state.duplicate_groups = manual_groups
                                st.session_state.current_page = 0
                                time.sleep(2)
                                st.rerun()
            
            if not manual_groups:
                st.markdown("---")
                st.markdown("""
                <div class="success-box" style="text-align: center;">
                    <h2 style="color: #155724;">✅ انتهى!</h2>
                    <p style="font-size: 1.2rem;">لا توجد ملفات مكررة تحتاج مراجعة</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🔄 إعادة المسح", use_container_width=True):
                    st.session_state.scan_completed = False
                    st.session_state.duplicate_groups = []
                    st.session_state.current_page = 0
                    st.rerun()
            else:
                st.markdown("---")
                st.markdown("### 👤 المجموعات التي تحتاج مراجعة يدوية")
                st.caption("هذه المجموعات تحتوي على أرقام متسلسلة (قد تكون أجزاء مختلفة)")
                
                if st.button("🔄 إعادة المسح", use_container_width=True):
                    st.session_state.scan_completed = False
                    st.session_state.duplicate_groups = []
                    st.session_state.current_page = 0
                    st.rerun()
                
                st.markdown("---")
                
                total_groups = len(manual_groups)
                if total_groups == 0:
                    st.stop()
                    
                total_pages = (total_groups + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
                current_page = st.session_state.current_page
                
                start_idx = current_page * ITEMS_PER_PAGE
                end_idx = min(start_idx + ITEMS_PER_PAGE, total_groups)
                
                st.info(f"📄 الصفحة {current_page + 1} من {total_pages} | عرض المجموعات {start_idx + 1} - {end_idx} من {total_groups}")
                
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
                
                current_groups = manual_groups[start_idx:end_idx]
                
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
                            # تنظيف الوصف من الروابط
                            clean_caption = clean_description(file['caption'])
                            
                            st.markdown(f"""
                            <div class="file-info">
                                <p><strong>الاسم:</strong> {file['name']}</p>
                                <p><strong>الحجم:</strong> {file['size'] / (1024*1024):.2f} ميجابايت</p>
                                <p><strong>التاريخ:</strong> {file['date'].strftime('%Y-%m-%d %H:%M')}</p>
                                <p><strong>الوصف:</strong> {clean_caption[:100] if len(clean_caption) > 100 else clean_caption}</p>
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
                                            st.warning("لم نتمكن من حساب عدد الصفحات")
                            
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
                                                
                                                for i, g in enumerate(manual_groups):
                                                    for j, f in enumerate(g):
                                                        if f['id'] == file['id']:
                                                            del manual_groups[i][j]
                                                            
                                                            if len(manual_groups[i]) <= 1:
                                                                del manual_groups[i]
                                                            
                                                            break
                                                
                                                if len(manual_groups) == 0:
                                                    st.session_state.current_page = 0
                                                elif st.session_state.current_page * ITEMS_PER_PAGE >= len(manual_groups):
                                                    st.session_state.current_page = max(0, st.session_state.current_page - 1)
                                                
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("فشل الحذف")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                
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

# ==========================================# ==========================================
# 🛑 شاشة الانتظار
# ==========================================
if status == False:
    st.markdown("""
    <div class="library-header">
        <div class="library-title">المكتبة الرقمية</div>
        <div class="library-subtitle">نظام البحث في الكتب والمراجع</div>
    </div>
    """, unsafe_allow_html=True)
    
    # تحديث الوقت الأخير بناءً على النشاط
    state.last_activity = time.time()  # التحديث عند الدخول إلى شاشة الانتظار
    time_passed = int(time.time() - state.last_activity)  # الوقت الذي مر منذ آخر نشاط
    time_left = TIMEOUT_SECONDS - time_passed  # الوقت المتبقي
    if time_left < 0: time_left = 0  # التأكد من أن الوقت المتبقي لا يصبح سالباً
    
    st.markdown(f"""
    <div class="waiting-container">
        <div class="waiting-title">⏸️ النظام مشغول حالياً</div>
        <div class="waiting-text">
            يستخدم أحد الباحثين النظام في الوقت الحالي.<br>
            للحفاظ على استقرار الخدمة، يُسمح بدخول مستخدم واحد فقط في كل مرة.
        </div>
        <div class="timer-display">{time_left} ثانية</div>
        <div class="waiting-text" style="font-size: 0.95rem;">
            سيتم إتاحة النظام تلقائياً عند انتهاء المدة المحددة
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("تحديث الحالة", use_container_width=True):
            state.last_activity = time.time()  # تحديث الوقت عند الضغط على "تحديث الحالة"
            st.rerun()  # إعادة تحميل الصفحة لعرض الوقت المتبقي بشكل جديد
    
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
        placeholder="ابحث عن كتاب، مؤلف، أو موضوع... (اكتب هنا)",
        label_visibility="collapsed",
        key="search_input"
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
        caption_text = clean_description(item['caption'])
        
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
