import streamlit as st
import asyncio
import time
import fitz  # PyMuPDF
from datetime import datetime
import os
from telethon.sync import TelegramClient
from telethon.tl.types import DocumentAttributeFilename
import hashlib

# تهيئة الصفحة
st.set_page_config(
    page_title="مكتبة الكزانة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS مخصص للتصميم الفاخر
st.markdown("""
<style>
    /* خلفية متدرجة فاخرة */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        color: #ffffff;
    }
    
    /* تنسيق الحاويات */
    .luxury-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border-radius: 20px;
        padding: 40px;
        margin: 30px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        transition: all 0.3s ease;
    }
    
    .luxury-container:hover {
        box-shadow: 0 16px 50px rgba(0, 0, 0, 0.6);
        transform: translateY(-5px);
    }
    
    /* أزرار فاخرة */
    .stButton > button {
        background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 18px 36px;
        border-radius: 50px;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        letter-spacing: 1px;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.6);
    }
    
    /* حقول الإدخال الأنيقة */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.08);
        border: 2px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        color: white;
        padding: 18px;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.3);
        background: rgba(255, 255, 255, 0.12);
    }
    
    .stTextInput > div > div > input::placeholder {
        color: rgba(255, 255, 255, 0.6);
    }
    
    /* عناوين أنيقة */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 300;
        letter-spacing: 3px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* رسائل النجاح والخطأ */
    .stSuccess {
        background: rgba(46, 204, 113, 0.15);
        border: 1px solid rgba(46, 204, 113, 0.4);
        border-radius: 15px;
        padding: 20px;
        backdrop-filter: blur(10px);
    }
    
    .stError {
        background: rgba(231, 76, 60, 0.15);
        border: 1px solid rgba(231, 76, 60, 0.4);
        border-radius: 15px;
        padding: 20px;
        backdrop-filter: blur(10px);
    }
    
    /* إكسباندر أنيق */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        font-weight: 500;
    }
    
    /* عداد الثواني */
    .timer {
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        padding: 15px 25px;
        border-radius: 25px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        font-weight: 600;
        font-size: 18px;
        z-index: 1000;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# تهيئة حالة الجلسة
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'admin_scan_completed' not in st.session_state:
    st.session_state.admin_scan_completed = False
if 'admin_duplicate_groups' not in st.session_state:
    st.session_state.admin_duplicate_groups = []
if 'admin_current_page' not in st.session_state:
    st.session_state.admin_current_page = 0
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'start_time' not in st.session_state:
    st.session_state.start_time = time.time()

# دوال المكتبة الأساسية
async def scan_for_duplicates():
    """يفحص القناة للبحث عن الملفات المكررة"""
    api_id = st.secrets["telegram"]["api_id"]
    api_hash = st.secrets["telegram"]["api_hash"]
    channel_id = st.secrets["telegram"]["channel_id"]
    
    async with TelegramClient('session', api_id, api_hash) as client:
        duplicate_groups = []
        file_hashes = {}
        
        async for message in client.iter_messages(channel_id):
            if message.document and message.document.size > 0:
                file_hash = hashlib.md5(f"{message.document.id}_{message.document.size}".encode()).hexdigest()
                
                if file_hash in file_hashes:
                    file_hashes[file_hash].append({
                        'id': message.id,
                        'name': get_file_name(message),
                        'size': message.document.size,
                        'date': message.date,
                        'caption': message.text
                    })
                else:
                    file_hashes[file_hash] = [{
                        'id': message.id,
                        'name': get_file_name(message),
                        'size': message.document.size,
                        'date': message.date,
                        'caption': message.text
                    }]
        
        # تصفية الملفات المكررة فقط
        for file_hash, files in file_hashes.items():
            if len(files) > 1:
                duplicate_groups.append(files)
        
        return duplicate_groups

def get_file_name(message):
    """يستخرج اسم الملف من رسالة التليغرام"""
    for attr in message.document.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            return attr.file_name
    return f"ملف_{message.document.id}"

def get_pdf_page_count(file_id):
    """يحسب عدد صفحات ملف PDF"""
    try:
        api_id = st.secrets["telegram"]["api_id"]
        api_hash = st.secrets["telegram"]["api_hash"]
        channel_id = st.secrets["telegram"]["channel_id"]
        
        with TelegramClient('session', api_id, api_hash) as client:
            message = client.get_messages(channel_id, ids=file_id)
            if message and message.document:
                file_path = client.download_media(message.document)
                if file_path and file_path.endswith('.pdf'):
                    doc = fitz.open(file_path)
                    pages = doc.page_count
                    doc.close()
                    os.remove(file_path)
                    return pages
    except Exception as e:
        st.error(f"خطأ في حساب الصفحات: {e}")
    return None

async def delete_file(file_id):
    """يحذف ملف من القناة"""
    try:
        api_id = st.secrets["telegram"]["api_id"]
        api_hash = st.secrets["telegram"]["api_hash"]
        channel_id = st.secrets["telegram"]["channel_id"]
        
        async with TelegramClient('session', api_id, api_hash) as client:
            await client.delete_messages(channel_id, file_id)
            return True
    except Exception as e:
        st.error(f"خطأ في حذف الملف: {e}")
        return False

async def search_books_async(query):
    """يبحث عن الكتب في القناة"""
    try:
        api_id = st.secrets["telegram"]["api_id"]
        api_hash = st.secrets["telegram"]["api_hash"]
        channel_id = st.secrets["telegram"]["channel_id"]
        
        results = []
        
        async with TelegramClient('session', api_id, api_hash) as client:
            async for message in client.iter_messages(channel_id, search=query):
                if message.document:
                    results.append({
                        'title': get_file_name(message),
                        'author': 'غير متاح',
                        'year': message.date.year,
                        'description': message.text[:200] if message.text else 'لا يوجد وصف'
                    })
        
        return results
    except Exception as e:
        st.error(f"خطأ في البحث: {e}")
        return []

# عداد الثواني
def show_timer():
    elapsed = int(time.time() - st.session_state.start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    
    st.markdown(f"""
        <div class="timer">
            <span style="color: #667eea;">المدة:</span> 
            <span style="color: white;">{minutes:02d}:{seconds:02d}</span>
        </div>
    """, unsafe_allow_html=True)

# عرض العداد
show_timer()

# الواجهة الرئيسية
st.markdown("<h1 style='text-align: center; margin-bottom: 50px; font-size: 3em;'>مكتبة الكزانة الرقمية</h1>", unsafe_allow_html=True)

if st.session_state.is_admin:
    # واجهة المسؤول
    st.markdown("<div class='luxury-container'>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("خروج من وضع الإدارة", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    
    st.markdown("---")
    
    # مسح الملفات المكررة
    st.markdown("<h3>نظام إدارة الملفات المتطابق</h3>", unsafe_allow_html=True)
    
    if not st.session_state.admin_scan_completed:
        st.markdown("<p style='text-align: center; margin: 30px 0; opacity: 0.8;'>ابدأ عملية فحص المكتبة للكشف عن الملفات المتطابقة</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("بدء الفحص", use_container_width=True, type="primary"):
                with st.spinner("جاري فحص المكتبة..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    duplicates = loop.run_until_complete(scan_for_duplicates())
                    loop.close()
                    
                    st.session_state.admin_duplicate_groups = duplicates
                    st.session_state.admin_scan_completed = True
                    st.session_state.admin_current_page = 0
                    st.rerun()
    else:
        total_groups = len(st.session_state.admin_duplicate_groups)
        
        if total_groups == 0:
            st.success("لا توجد ملفات متطابقة في المكتبة")
        else:
            st.info(f"تم العثور على {total_groups} مجموعة من الملفات المتطابقة")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("إعادة الفحص", use_container_width=True):
                st.session_state.admin_scan_completed = False
                st.session_state.admin_duplicate_groups = []
                st.session_state.admin_current_page = 0
                st.rerun()
        
        # عرض النتائج
        if total_groups > 0:
            page_size = 5
            start_idx = st.session_state.admin_current_page * page_size
            end_idx = start_idx + page_size
            displayed_groups = st.session_state.admin_duplicate_groups[start_idx:end_idx]
            
            for idx, group in enumerate(displayed_groups, start_idx + 1):
                with st.expander(f"المجموعة {idx}: {len(group)} ملف متطابق", expanded=False):
                    for file_idx, file in enumerate(group, 1):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.markdown(f"**{file['name']}**")
                            st.caption(f"الحجم: {file['size'] / (1024*1024):.2f} ميجابايت")
                        
                        with col2:
                            if st.button("فحص", key=f"check_{file['id']}"):
                                pages = get_pdf_page_count(file['id'])
                                if pages:
                                    st.success(f"{pages} صفحة")
                                else:
                                    st.warning("غير متاح")
                        
                        with col3:
                            if st.button("حذف", key=f"delete_{file['id']}", type="secondary"):
                                st.warning(f"هل أنت متأكد من حذف: {file['name']}?")
                                if st.button("تأكيد الحذف", key=f"confirm_{file['id']}"):
                                    with st.spinner("جاري الحذف..."):
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        success = loop.run_until_complete(delete_file(file['id']))
                                        loop.close()
                                        
                                        if success:
                                            st.success("تم الحذف بنجاح")
                                            time.sleep(1)
                                            st.session_state.admin_scan_completed = False
                                            st.rerun()
                                        else:
                                            st.error("فشل الحذف")
            
            # التنقل بين الصفحات
            if total_groups > page_size:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    if st.session_state.admin_current_page > 0:
                        if st.button("السابق", use_container_width=True):
                            st.session_state.admin_current_page -= 1
                            st.rerun()
                
                with col2:
                    st.markdown(f"<p style='text-align: center;'>صفحة {st.session_state.admin_current_page + 1} من {((total_groups - 1) // page_size) + 1}</p>", unsafe_allow_html=True)
                
                with col3:
                    if end_idx < total_groups:
                        if st.button("التالي", use_container_width=True):
                            st.session_state.admin_current_page += 1
                            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

else:
    # واجهة المستخدم العادي
    st.markdown("<div class='luxury-container'>", unsafe_allow_html=True)
    
    # دخول المسؤول
    with st.expander("دخول المسؤول", expanded=False):
        password = st.text_input("كلمة المرور:", type="password", placeholder="أدخل كلمة مرور المسؤول")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("دخول", use_container_width=True):
                if password == st.secrets["admin_password"]:
                    st.session_state.is_admin = True
                    st.success("تم الدخول بنجاح")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("كلمة مرور خاطئة")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # البحث في الكتب
    st.markdown("<div class='luxury-container'>", unsafe_allow_html=True)
    st.markdown("<h3>البحث في المكتبة</h3>", unsafe_allow_html=True)
    
    query = st.text_input("ابحث عن كتاب أو موضوع:", placeholder="أدخل اسم الكتاب أو الكلمة المفتاحية")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("بحث", use_container_width=True, type="primary"):
            if query:
                with st.spinner("جاري البحث..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(search_books_async(query))
                    loop.close()
                    st.session_state.search_results = results
                    st.session_state.search_time = time.time()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # عرض نتائج البحث
    if st.session_state.search_results:
        st.markdown("<div class='luxury-container'>", unsafe_allow_html=True)
        
        if st.session_state.search_results:
            st.markdown(f"<h4>نتائج البحث: {len(st.session_state.search_results)} كتاب</h4>", unsafe_allow_html=True)
            
            for book in st.session_state.search_results:
                with st.expander(f"📖 {book.get('title', 'كتاب')}", expanded=False):
                    st.markdown(f"**المؤلف:** {book.get('author', 'غير متاح')}")
                    st.markdown(f"**السنة:** {book.get('year', 'غير متاح')}")
                    st.markdown(f"**الوصف:** {book.get('description', 'لا يوجد وصف')}")
        else:
            st.info("لم يتم العثور على نتائج")
        
        st.markdown("</div>", unsafe_allow_html=True)
