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

# --- تصميم CSS احترافي يشبه محركات البحث مثل Google ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Product+Sans:wght@400;700&display=swap');
    
    * {
        font-family: 'Product Sans', sans-serif;
    }
    
    body {
        background-color: #FFFFFF;
    }
    
    .stApp {
        max-width: 800px;
        margin: 0 auto;
        padding-top: 10vh;
    }
    
    h1, h2, h3 {
        font-family: 'Product Sans', sans-serif;
        text-align: center;
    }

    /* تصميم حقل البحث مثل Google */
    .stTextInput > div > div > input {
        border: 1px solid #DFE1E5 !important;
        border-radius: 24px !important;
        padding: 13px 20px !important;
        font-size: 16px !important;
        background: white !important;
        color: #202124 !important;
        width: 100% !important;
        box-shadow: 0 1px 6px 0 rgba(32,33,36,0.28);
        transition: box-shadow 0.3s;
    }

    .stTextInput > div > div > input:hover,
    .stTextInput > div > div > input:focus {
        box-shadow: 0 1px 6px 0 rgba(32,33,36,0.28);
        border-color: #DFE1E5 !important;
    }

    /* تصميم الأزرار مثل Google */
    .stButton > button {
        background-color: #F8F9FA;
        color: #3C4043;
        border: 1px solid #F8F9FA;
        border-radius: 4px;
        padding: 10px 20px;
        font-size: 14px;
        margin: 11px 4px;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        border: 1px solid #DADCE0;
        box-shadow: 0 1px 1px rgba(0,0,0,.1);
    }

    /* شعار مثل Google */
    .google-logo {
        text-align: center;
        margin-bottom: 20px;
        font-size: 64px;
        font-weight: bold;
        color: #4285F4;
    }
    
    .google-logo span:nth-child(1) { color: #4285F4; }
    .google-logo span:nth-child(2) { color: #EA4335; }
    .google-logo span:nth-child(3) { color: #FBBC05; }
    .google-logo span:nth-child(4) { color: #4285F4; }
    .google-logo span:nth-child(5) { color: #34A853; }
    .google-logo span:nth-child(6) { color: #EA4335; }

    /* إخفاء عناصر غير مرغوبة */
    footer {visibility: hidden;}
    header {visibility: hidden;}
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

# ==========================================
# الواجهة الرئيسية المشابهة لـ Google
# ==========================================
st.markdown("""
<div class="google-logo">
    <span>ب</span><span>ا</span><span>ح</span><span>ث</span><span> </span><span>ا</span><span>ل</span><span>ك</span><span>ت</span><span>ب</span>
</div>
""", unsafe_allow_html=True)

query = st.text_input("", placeholder="ابحث عن كتاب...", key="search_query")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    st.button("بحث في الكتب", on_click=lambda: st.session_state.search_results = search_books_async(query))
with col_btn2:
    st.button("أشعر بالحظ", on_click=lambda: st.write("ميزة قادمة قريباً..."))