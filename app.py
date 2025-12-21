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
from collections import defaultdict  # إضافة لدعم إدارة المكررات

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
    /* خلفية وألوان عامة */
    .stApp {
        background-color: #f9f9f9;
        color: #333333;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* الهيدر */
    .header {
        background-color: #2c3e50;
        padding: 20px;
        text-align: center;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    
    .header h1 {
        color: white;
        font-size: 28px;
        margin: 0;
    }
    
    .header p {
        color: #bdc3c7;
        font-size: 16px;
        margin: 5px 0 0;
    }
    
    /* البادج */
    .badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
    }
    
    .badge-admin {
        background-color: #e74c3c;
        color: white;
    }
    
    .badge-user {
        background-color: #3498db;
        color: white;
    }
    
    /* الزر */
    .stButton > button {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 10px 20px;
        font-size: 16px;
        transition: background-color 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #2980b9;
    }
    
    /* الإكسباندير */
    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        background-color: white;
    }
    
    /* التنبيهات */
    .stAlert {
        border-radius: 4px;
        padding: 15px;
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
    # تنظيف الذاكرة
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
# 🛑 شاشة الانتظار
# ==========================================
if status == False:
    st.markdown("""
<div class="header">
    <h1>المكتبة الرقمية</h1>
    <p>نظام البحث في الكتب والمراجع</p>
</div>
""", unsafe_allow_html=True)
    
    time_passed = int(time.time() - state.last_activity)
    time_left = TIMEOUT_SECONDS - time_passed
    if time_left < 0: time_left = 0
    
    st.markdown("""
<div style="text-align: center; padding: 20px; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h3>⏸️ النظام مشغول حالياً</h3>
    <p>يستخدم أحد الباحثين النظام في الوقت الحالي.</p>
    <p>للحفاظ على استقرار الخدمة، يُسمح بدخول مستخدم واحد فقط في كل مرة.</p>
    <h4>{} ثانية</h4>
    <p>سيتم إتاحة النظام تلقائياً عند انتهاء المدة المحددة</p>
</div>
""".format(time_left), unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("تحديث الحالة", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    # صندوق إنهاء الجلسة للمشرف
    with st.expander("🔐 لوحة تحكم المشرف"):
        st.markdown('<br>', unsafe_allow_html=True)
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
        
        st.markdown('<br>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    with st.expander("دخول المسؤول"):
        password_attempt = st.text_input("كلمة المرور:", type="password", key="admin_pass_locked")
        if st.button("دخول"):
            if password_attempt == st.secrets["admin_password"]:
                st.session_state.is_admin = True
                st.success("تم التحقق من الهوية")
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
<div class="header">
    <h1>المكتبة الرقمية</h1>
    <p>نظام البحث في الكتب والمراجع</p>
</div>
""", unsafe_allow_html=True)
    
    st.markdown("""
<div style="text-align: center; padding: 20px; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h3>مرحباً بك في المكتبة</h3>
    <p>يوفر لك هذا النظام إمكانية البحث في آلاف الكتب والمراجع العلمية والأدبية<br>
    من مختلف المجالات المعرفية. استخدم محرك البحث للعثور على الكتاب المطلوب<br>
    وتحميله مباشرة إلى جهازك.</p>
    <h4>النظام متاح الآن</h4>
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
<div class="header">
    <h1>المكتبة الرقمية</h1>
    <p>نظام البحث في الكتب والمراجع</p>
</div>
""", unsafe_allow_html=True)

# شريط المعلومات العلوي
if st.session_state.is_admin:
    status_badge = '<span class="badge badge-admin">وضع الإدارة</span>'
else:
    time_left_session = TIMEOUT_SECONDS - int(time.time() - state.last_activity)
    status_badge = f'<span class="badge badge-user">وقت متبقي: {time_left_session} ث</span>'

col_info1, col_info2, col_info3 = st.columns([2, 6, 2])

with col_info1:
    st.markdown(f'<div style="text-align: left;">{status_badge}</div>', unsafe_allow_html=True)

with col_info3:
    if st.button("إنهاء الجلسة", use_container_width=True):
        if st.session_state.is_admin:
            st.session_state.is_admin = False
        else:
            state.locked = False
            state.current_user_token = None
        clear_session_data()  # تنظيف البيانات عند الخروج
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
                # zoom للحصول على جودة أفضل (2 = دقة عالية)
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

# --- دوال إدارة المكررات (من admin.py) ---
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

# --- حالة الإدارة (من admin.py، مع تعديل لعدم التداخل) ---
if 'admin_duplicate_groups' not in st.session_state:
    st.session_state.admin_duplicate_groups = []

if 'admin_scan_completed' not in st.session_state:
    st.session_state.admin_scan_completed = False

# --- واجهة المستخدم الرئيسية مع التبويبات ---
st.markdown("---")

if st.session_state.is_admin:
    tab_search, tab_admin = st.tabs(["البحث في الكتب", "إدارة المكررات"])

    with tab_search:
        # واجهة البحث (الجزء المفقود من app.py، تم إعادة بناؤه بناءً على السياق)
        if 'search_results' not in st.session_state:
            st.session_state.search_results = []
        if 'search_time' not in st.session_state:
            st.session_state.search_time = None

        st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h3>البحث في الكتب</h3>
        </div>
        """, unsafe_allow_html=True)

        query = st.text_input("أدخل اسم الكتاب أو الكلمة المفتاحية:", key="search_query")

        col_btn = st.columns(3)
        with col_btn[1]:
            if st.button("بدء البحث", use_container_width=True):
                with st.spinner("جاري البحث..."):
                    results = search_books_async(query)
                    st.session_state.search_results = results
                    st.session_state.search_time = time.time()

        if st.session_state.search_results:
            st.markdown(f"**عدد النتائج:** {len(st.session_state.search_results)}")
            for result in st.session_state.search_results:
                with st.expander(result['file_name']):
                    st.write(f"الحجم: {result['size'] / (1024*1024):.2f} MB")
                    st.write(f"التاريخ: {result['date']}")
                    st.write(f"الوصف: {result['caption'][:200]}...")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("تحميل الكتاب", key=f"dl_{result['id']}"):
                            buffer, file_name = download_book_to_memory(result['id'])
                            if buffer:
                                st.download_button("تحميل الآن", data=buffer, file_name=file_name, mime="application/pdf")
                    with col2:
                        if st.button("عدد الصفحات", key=f"pages_{result['id']}"):
                            pages = get_pdf_page_count(result['id'])
                            if pages:
                                st.success(f"عدد الصفحات: {pages}")
                    with col3:
                        if st.button("معاينة الصفحة الأولى", key=f"prev_{result['id']}"):
                            img = get_first_page_preview(result['id'])
                            if img:
                                st.image(img, caption="الصفحة الأولى")

    with tab_admin:
        # واجهة إدارة المكررات (من admin.py)
        st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h3>إدارة الملفات المكررة</h3>
            <p>نظام الكشف والحذف الذكي</p>
        </div>
        """, unsafe_allow_html=True)

        st.info("**الجلسات الأخرى متوقفة** - أنت الوحيد المسموح له بالدخول حالياً")

        st.markdown("---")

        if not st.session_state.admin_scan_completed:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("""
                <div style="text-align: center;">
                    <h4>ابدأ عملية المسح</h4>
                    <p>سيتم فحص جميع الملفات في القناة للبحث عن المكررات</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("بدء المسح الآن", use_container_width=True, type="primary"):
                    with st.spinner("جاري مسح القناة... قد يستغرق بعض الوقت"):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        duplicates = loop.run_until_complete(scan_for_duplicates())
                        loop.close()
                        
                        st.session_state.admin_duplicate_groups = duplicates
                        st.session_state.admin_scan_completed = True
                        st.rerun()
        else:
            if len(st.session_state.admin_duplicate_groups) == 0:
                st.markdown("""
                <div style="text-align: center; padding: 20px; background-color: white; border-radius: 8px;">
                    <h2>رائع!</h2>
                    <p>لا توجد ملفات مكررة في القناة</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("إعادة المسح", use_container_width=True):
                    st.session_state.admin_scan_completed = False
                    st.session_state.admin_duplicate_groups = []
                    st.rerun()
            else:
                st.success(f"تم العثور على **{len(st.session_state.admin_duplicate_groups)}** مجموعة من الملفات المحتملة المكررة")
                
                if st.button("إعادة المسح", use_container_width=True):
                    st.session_state.admin_scan_completed = False
                    st.session_state.admin_duplicate_groups = []
                    st.rerun()
                
                st.markdown("---")
                
                # عرض المجموعات المكررة
                for idx, group in enumerate(st.session_state.admin_duplicate_groups, 1):
                    st.markdown(f"""
                    <div style="padding: 10px; background-color: white; border-radius: 8px; margin-bottom: 20px;">
                        <h4>مجموعة مكررة #{idx}</h4>
                        <p><strong>الحجم المشترك:</strong> {group[0]['size'] / (1024*1024):.2f} ميجابايت</p>
                        <p><strong>عدد الملفات:</strong> {len(group)} ملف</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # عرض كل ملف في المجموعة
                    for file_idx, file in enumerate(group, 1):
                        with st.expander(f"الملف {file_idx}: {file['name']}", expanded=True):
                            st.markdown(f"""
                            <p><strong>الاسم:</strong> {file['name']}</p>
                            <p><strong>الحجم:</strong> {file['size'] / (1024*1024):.2f} ميجابايت</p>
                            <p><strong>التاريخ:</strong> {file['date'].strftime('%Y-%m-%d %H:%M')}</p>
                            <p><strong>الوصف:</strong> {file['caption'][:100] if file['caption'] else 'لا يوجد'}</p>
                            """, unsafe_allow_html=True)
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button(f"فحص عدد الصفحات", key=f"admin_check_pages_{file['id']}"):
                                    with st.spinner("جاري الفحص..."):
                                        pages = get_pdf_page_count(file['id'])  # استخدام دالة app.py الموحدة
                                        if pages:
                                            st.success(f"عدد الصفحات: {pages}")
                                        else:
                                            st.warning("لم نتمكن من حساب عدد الصفحات (قد لا يكون PDF)")
                            
                            with col2:
                                delete_key = f"admin_delete_{file['id']}"
                                if st.button(f"حذف هذا الملف", key=delete_key, type="primary"):
                                    st.warning("تأكيد الحذف")
                                    confirm_key = f"admin_confirm_{file['id']}"
                                    if st.button(f"نعم، احذف نهائياً", key=confirm_key):
                                        with st.spinner("جاري الحذف..."):
                                            loop = asyncio.new_event_loop()
                                            asyncio.set_event_loop(loop)
                                            success = loop.run_until_complete(delete_file(file['id']))
                                            loop.close()
                                            
                                            if success:
                                                st.success("تم الحذف بنجاح!")
                                                time.sleep(1)
                                                # إعادة المسح
                                                st.session_state.admin_scan_completed = False
                                                st.session_state.admin_duplicate_groups = []
                                                st.rerun()
                                            else:
                                                st.error("فشل الحذف")
                    
                    st.markdown("<br>", unsafe_allow_html=True)

else:
    # واجهة البحث فقط للمستخدم العادي
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'search_time' not in st.session_state:
        st.session_state.search_time = None

    st.markdown("""
    <div style="text-align: center; padding: 10px;">
        <h3>البحث في الكتب</h3>
    </div>
    """, unsafe_allow_html=True)

    query = st.text_input("أدخل اسم الكتاب أو الكلمة المفتاحية:", key="search_query_nonadmin")

    col_btn = st.columns(3)
    with col_btn[1]:
        if st.button("بدء البحث", use_container_width=True):
            with st.spinner("جاري البحث..."):
                results = search_books_async(query)
                st.session_state.search_results = results
                st.session_state.search_time = time.time()

    if st.session_state.search_results:
        st.markdown(f"**عدد النتائج:** {len(st.session_state.search_results)}")
        for result in st.session_state.search_results:
            with st.expander(result['file_name']):
                st.write(f"الحجم: {result['size'] / (1024*1024):.2f} MB")
                st.write(f"التاريخ: {result['date']}")
                st.write(f"الوصف: {result['caption'][:200]}...")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("تحميل الكتاب", key=f"dl_nonadmin_{result['id']}"):
                        buffer, file_name = download_book_to_memory(result['id'])
                        if buffer:
                            st.download_button("تحميل الآن", data=buffer, file_name=file_name, mime="application/pdf")
                with col2:
                    if st.button("عدد الصفحات", key=f"pages_nonadmin_{result['id']}"):
                        pages = get_pdf_page_count(result['id'])
                        if pages:
                            st.success(f"عدد الصفحات: {pages}")
                with col3:
                    if st.button("معاينة الصفحة الأولى", key=f"prev_nonadmin_{result['id']}"):
                        img = get_first_page_preview(result['id'])
                        if img:
                            st.image(img, caption="الصفحة الأولى")