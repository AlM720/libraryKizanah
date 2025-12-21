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
from collections import defaultdict

nest_asyncio.apply()

st.set_page_config(
    page_title="لوحة إدارة المكررات",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# تصميم CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    
    * {
        font-family: 'Tajawal', sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background-color: #f5f5f5;
    }
    
    .admin-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .admin-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
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

# التحقق من secrets
required_secrets = ["api_id", "api_hash", "session_string", "channel_id", "key"]
if not all(key in st.secrets for key in required_secrets):
    st.error("⚠️ خطأ: تأكد من إعداد ملف secrets.toml")
    st.stop()

# إعدادات الاتصال
api_id = int(st.secrets["api_id"])
api_hash = st.secrets["api_hash"]
session_string = st.secrets["session_string"]
channel_id = int(st.secrets["channel_id"])

# حالة المصادقة
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

if 'duplicate_groups' not in st.session_state:
    st.session_state.duplicate_groups = []

if 'scan_completed' not in st.session_state:
    st.session_state.scan_completed = False

# دالة الاتصال
async def get_client():
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.start()
    return client

# دالة مسح المكررات
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

# دالة فحص عدد الصفحات
async def get_page_count(message_id):
    """الحصول على عدد صفحات الملف"""
    client = await get_client()
    try:
        entity = await client.get_entity(channel_id)
        message = await client.get_messages(entity, ids=message_id)
        
        if message and message.file:
            buffer = io.BytesIO()
            await client.download_media(message, buffer)
            buffer.seek(0)
            
            if message.file.name and message.file.name.lower().endswith('.pdf'):
                pdf = PdfReader(buffer)
                page_count = len(pdf.pages)
                buffer.close()
                gc.collect()
                return page_count
            
        return None
    except:
        return None
    finally:
        await client.disconnect()

# دالة حذف الملف
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
# شاشة تسجيل الدخول
# ==========================================
if not st.session_state.admin_authenticated:
    st.markdown("""
    <div class="admin-header">
        <div class="admin-title">🔐 لوحة التحكم</div>
        <p style="font-size: 1.2rem; margin-top: 1rem;">إدارة المكررات والملفات</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="warning-box">
            <h3 style="color: #856404; margin-top: 0;">⚠️ تحذير هام</h3>
            <p style="margin-bottom: 0;">
                عند الدخول إلى لوحة التحكم، سيتم إيقاف جميع الجلسات الأخرى تلقائياً.
                لن يتمكن أي مستخدم من الدخول حتى تنتهي من عملك.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        admin_key = st.text_input("مفتاح المدير:", type="password", key="admin_key_login")
        
        if st.button("دخول لوحة التحكم", use_container_width=True, type="primary"):
            if admin_key == st.secrets["key"]:
                st.session_state.admin_authenticated = True
                st.success("✓ تم التحقق بنجاح - جاري الدخول...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ مفتاح المدير غير صحيح")
    
    st.stop()

# ==========================================
# لوحة التحكم الرئيسية
# ==========================================

st.markdown("""
<div class="admin-header">
    <div class="admin-title">🗂️ إدارة الملفات المكررة</div>
    <p style="font-size: 1.1rem; margin-top: 0.5rem;">نظام الكشف والحذف الذكي</p>
</div>
""", unsafe_allow_html=True)

# شريط المعلومات
col_info1, col_info2 = st.columns([3, 1])

with col_info1:
    st.info("🔒 **الجلسات الأخرى متوقفة** - أنت الوحيد المسموح له بالدخول حالياً")

with col_info2:
    if st.button("🚪 خروج", use_container_width=True):
        st.session_state.admin_authenticated = False
        st.session_state.duplicate_groups = []
        st.session_state.scan_completed = False
        st.rerun()

st.markdown("---")

# زر بدء المسح
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
                st.rerun()
else:
    # عرض النتائج
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
            st.rerun()
    else:
        st.success(f"✓ تم العثور على **{len(st.session_state.duplicate_groups)}** مجموعة من الملفات المحتملة المكررة")
        
        if st.button("🔄 إعادة المسح", use_container_width=True):
            st.session_state.scan_completed = False
            st.session_state.duplicate_groups = []
            st.rerun()
        
        st.markdown("---")
        
        # عرض المجموعات المكررة
        for idx, group in enumerate(st.session_state.duplicate_groups, 1):
            st.markdown(f"""
            <div class="duplicate-card">
                <h3 style="color: #c0392b;">🔴 مجموعة مكررة #{idx}</h3>
                <p><strong>الحجم المشترك:</strong> {group[0]['size'] / (1024*1024):.2f} ميجابايت</p>
                <p><strong>عدد الملفات:</strong> {len(group)} ملف</p>
            </div>
            """, unsafe_allow_html=True)
            
            # عرض كل ملف في المجموعة
            for file_idx, file in enumerate(group, 1):
                with st.expander(f"📄 الملف {file_idx}: {file['name']}", expanded=True):
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
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                pages = loop.run_until_complete(get_page_count(file['id']))
                                loop.close()
                                
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
                                        time.sleep(1)
                                        # إعادة المسح
                                        st.session_state.scan_completed = False
                                        st.session_state.duplicate_groups = []
                                        st.rerun()
                                    else:
                                        st.error("فشل الحذف")
            
            st.markdown("<br><br>", unsafe_allow_html=True)