import streamlit as st
import sqlite3
import requests
import time
import os
from datetime import datetime, timedelta
import tempfile
from pathlib import Path
import hashlib
import re

# ═══════════════════════════════════════════════════════════════
# 🎨 إعدادات الصفحة والتصميم
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="المكتبة الرقمية الشاملة",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# استيراد خط عربي (Cairo) وتنسيق الواجهة
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    * {font-family: 'Cairo', sans-serif;}
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {background-color: #f8f9fa;}
    
    /* Toolbar styling */
    .toolbar {
        position: fixed; top: 0; left: 0; right: 0;
        background: white;
        padding: 0.8rem 2rem;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        z-index: 1000; direction: rtl;
        border-bottom: 3px solid #0e7490;
    }
    
    .app-title {
        color: #0e7490;
        font-weight: 700;
        font-size: 1.4rem;
        display: flex; align-items: center; gap: 10px;
    }
    
    /* Card Design */
    .book-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        transition: transform 0.2s, box-shadow 0.2s;
        direction: rtl;
        position: relative;
        overflow: hidden;
    }
    
    .book-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(14, 116, 144, 0.1);
        border-color: #0e7490;
    }
    
    .book-card::before {
        content: '';
        position: absolute;
        right: 0; top: 0; bottom: 0;
        width: 6px;
        background: #0e7490;
        border-radius: 0 4px 4px 0;
    }
    
    .book-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.8rem;
    }
    
    .book-meta {
        display: flex; gap: 1rem; align-items: center;
        color: #6b7280; font-size: 0.9rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }
    
    .meta-item {
        background: #f3f4f6;
        padding: 0.2rem 0.8rem;
        border-radius: 8px;
        display: flex; align-items: center; gap: 5px;
    }
    
    .book-desc {
        color: #4b5563;
        font-size: 0.95rem;
        line-height: 1.7;
        padding-top: 1rem;
        border-top: 1px dashed #e5e7eb;
        margin-top: 0.5rem;
    }

    /* Status Messages */
    .status-active {
        background: #ecfdf5; color: #047857;
        padding: 0.5rem 1rem; border-radius: 12px;
        font-weight: 600; font-size: 0.9rem;
        border: 1px solid #a7f3d0;
    }
    
    /* Admin Panel */
    .admin-panel {
        background: #fffbeb; border: 2px solid #fbbf24;
        padding: 1.5rem; border-radius: 12px; margin: 2rem 0;
        direction: rtl;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# ⚙️ الإعدادات (Backend)
# ═══════════════════════════════════════════════════════════════

try:
    BOT_TOKENS = [st.secrets["bot1"], st.secrets["bot2"], st.secrets["bot3"]]
    CHANNEL_ID = st.secrets["channelid"]
    ADMIN_PASSWORD = st.secrets["password"]
    GDRIVE_FILE_ID = st.secrets.get("gdrive_file_id", "")
    USER_API_ID = st.secrets.get("user_api_id", "")
    USER_API_HASH = st.secrets.get("user_api_hash", "")
    USER_SESSION_STRING = st.secrets.get("user_session_string", "")
except:
    st.error("⚠️ خطأ في إعدادات النظام الداخلي (Secrets)")
    st.stop()

DATABASE_FILE = "/tmp/books.db"
DB_CACHE_TIME = 300
SESSION_TIMEOUT = 600
MIN_REQUEST_INTERVAL = 3
MAX_REQUESTS_PER_MINUTE = 15
LARGE_FILE_MIN_INTERVAL = 8
LARGE_FILE_THRESHOLD_MB = 5
USER_SESSION_MIN_INTERVAL = 10
USER_SESSION_MAX_SIZE_MB = 2000

# ═══════════════════════════════════════════════════════════════
# 📦 إدارة الحالة (State Management)
# ═══════════════════════════════════════════════════════════════

for key in ['active_sessions', 'bot_requests', 'session_id', 'is_admin', 'show_counter', 
            'search_results', 'session_start_time', 'downloads_count', 'search_cache', 
            'search_history', 'db_loaded', 'db_last_update', 'db_size', 
            'last_download_time', 'last_large_download_time', 'downloading_now', 
            'last_user_session_download', 'user_session_downloads_count']:
    if key not in st.session_state:
        if key == 'bot_requests': st.session_state[key] = {i: [] for i in range(len(BOT_TOKENS))}
        elif key in ['active_sessions', 'search_cache', 'search_history']: st.session_state[key] = {}
        elif key in ['show_counter', 'is_admin', 'db_loaded', 'downloading_now']: st.session_state[key] = False
        elif key in ['downloads_count', 'db_last_update', 'db_size', 'user_session_downloads_count']: st.session_state[key] = 0
        elif key in ['last_download_time', 'last_large_download_time', 'last_user_session_download']: st.session_state[key] = 0.0
        else: st.session_state[key] = None

USER_SESSION_AVAILABLE = bool(USER_API_ID and USER_API_HASH and USER_SESSION_STRING)

# ═══════════════════════════════════════════════════════════════
# 🛠️ الدوال المساعدة (Backend Logic)
# ═══════════════════════════════════════════════════════════════

def extract_file_id(url_or_id):
    if not url_or_id: return None
    if len(url_or_id) < 50 and '/' not in url_or_id: return url_or_id
    patterns = [r'/file/d/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)', r'/folders/([a-zA-Z0-9_-]+)']
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match: return match.group(1)
    return url_or_id

def download_db_from_gdrive():
    if not GDRIVE_FILE_ID: return False
    if os.path.exists(DATABASE_FILE):
        if time.time() - os.path.getmtime(DATABASE_FILE) < DB_CACHE_TIME: return True
    try:
        file_id = extract_file_id(GDRIVE_FILE_ID)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(DATABASE_FILE, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk: f.write(chunk)
            st.session_state.db_loaded = True
            st.session_state.db_last_update = time.time()
            st.session_state.db_size = os.path.getsize(DATABASE_FILE) / (1024 * 1024)
            return True
    except: return False
    return False

def get_db_connection():
    if not st.session_state.db_loaded or not os.path.exists(DATABASE_FILE):
        if not download_db_from_gdrive(): return None
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except: return None

def normalize_arabic_text(text):
    if not text: return ""
    text = re.sub(r'[\u064B-\u065F]', '', text)
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return ' '.join(text.split()).lower().strip()

def search_books_advanced(query, filters=None, limit=50):
    if not query or len(query) < 2: return []
    filters = filters or {}
    words = [w for w in normalize_arabic_text(query).split() if len(w) > 1]
    if not words: return []
    
    conn = get_db_connection()
    if not conn: return []
    
    try:
        cursor = conn.cursor()
        sql_parts, params = [], []
        conditions = []
        for word in words:
            conditions.append("(file_name LIKE ? OR description LIKE ?)")
            params.extend([f'%{word}%', f'%{word}%'])
        sql_parts.append("(" + " AND ".join(conditions) + ")")
        
        if filters.get('format') and filters['format'] != 'all':
            sql_parts.append("file_extension = ?")
            params.append(filters['format'])
            
        where = " AND ".join(sql_parts)
        cursor.execute(f"SELECT * FROM books WHERE {where} LIMIT ?", params + [limit * 2])
        results = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return results[:limit]
    except: return []

# ═══════════════════════════════════════════════════════════════
# 📥 منطق التحميل (Hidden from User)
# ═══════════════════════════════════════════════════════════════

def get_best_bot():
    current_time = time.time()
    best_idx, min_req = 0, float('inf')
    for idx in range(len(BOT_TOKENS)):
        recent = [r for r in st.session_state.bot_requests[idx] if current_time - r < 60]
        st.session_state.bot_requests[idx] = recent
        if len(recent) < min_req: min_req, best_idx = len(recent), idx
    st.session_state.bot_requests[best_idx].append(current_time)
    return BOT_TOKENS[best_idx]

def get_telegram_file_url(file_id):
    """الحصول على رابط مباشر لملف Telegram للمعاينة"""
    try:
        bot_token = BOT_TOKENS[0]
        r = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={'file_id': file_id},
            timeout=5
        )
        
        if r.status_code == 200 and 'result' in r.json():
            path = r.json()['result']['file_path']
            direct_url = f"https://api.telegram.org/file/bot{bot_token}/{path}"
            return direct_url
    except:
        pass
    return None

def check_cooldowns(file_size_mb):
    current_time = time.time()
    if file_size_mb >= 20: 
        if not USER_SESSION_AVAILABLE: return False, 0, "unavailable"
        elapsed = current_time - st.session_state.last_user_session_download
        if elapsed < USER_SESSION_MIN_INTERVAL: return False, USER_SESSION_MIN_INTERVAL - elapsed, "user_session"
        return True, 0, "user_session"
    
    is_large = file_size_mb >= LARGE_FILE_THRESHOLD_MB
    last_time = st.session_state.last_large_download_time if is_large else st.session_state.last_download_time
    req_interval = LARGE_FILE_MIN_INTERVAL if is_large else MIN_REQUEST_INTERVAL
    
    elapsed = current_time - last_time
    if elapsed < req_interval: return False, req_interval - elapsed, "bot"
    return True, 0, "bot"

def unified_downloader(file_id, file_name, file_size_mb, file_ext):
    """دالة تحميل مركزية - إصلاح return tuple"""
    
    if st.session_state.downloading_now:
        st.warning("⏳ يرجى الانتظار، هناك ملف قيد التحميل حالياً.")
        return None, None

    can_download, wait_time, method = check_cooldowns(file_size_mb)
    
    if not can_download:
        if method == "unavailable":
            st.error("عذراً، هذا الملف غير متاح للتحميل حالياً.")
            if st.session_state.is_admin:
                st.info("💡 الملف يتطلب User Session غير متاح")
            return None, None
        
        msg_holder = st.empty()
        for i in range(int(wait_time), 0, -1):
            msg_holder.info(f"🔄 جاري تجهيز الملف... ({i} ثانية)")
            time.sleep(1)
        msg_holder.empty()

    st.session_state.downloading_now = True
    
    try:
        file_data = None
        
        # ملفات كبيرة (User Session)
        if file_size_mb >= 20:
            if not USER_SESSION_AVAILABLE:
                st.error("الملف كبير ولا يمكن تحميله حالياً.")
                if st.session_state.is_admin:
                    st.warning("⚙️ يتطلب User Session")
                return None, None
                
            from telethon.sync import TelegramClient
            from telethon.sessions import StringSession
            import io
            
            with st.spinner("📥 جاري التحميل..."):
                try:
                    client = TelegramClient(StringSession(USER_SESSION_STRING), USER_API_ID, USER_API_HASH)
                    with client:
                        file_buffer = io.BytesIO()
                        client.download_file(file_id, file=file_buffer)
                        file_buffer.seek(0)
                        file_data = file_buffer.read()
                        
                    st.session_state.last_user_session_download = time.time()
                    st.session_state.user_session_downloads_count += 1
                    
                    if st.session_state.is_admin:
                        st.success(f"✅ تم عبر User Session ({file_size_mb:.1f} MB)")
                        
                except Exception as e:
                    st.error("تعذر جلب الملف. يرجى المحاولة لاحقاً.")
                    if st.session_state.is_admin: st.error(f"🔧 {str(e)}")
                    return None, None
        
        # ملفات عادية (Bot API)
        else:
            bot_token = get_best_bot()
            with st.spinner("📥 جاري التحميل..."):
                try:
                    r = requests.get(f"https://api.telegram.org/bot{bot_token}/getFile", params={'file_id': file_id}, timeout=10)
                    if r.status_code == 200 and 'result' in r.json():
                        path = r.json()['result']['file_path']
                        dl_url = f"https://api.telegram.org/file/bot{bot_token}/{path}"
                        file_res = requests.get(dl_url, stream=True, timeout=30)
                        if file_res.status_code == 200:
                            file_data = file_res.content
                            if file_size_mb >= LARGE_FILE_THRESHOLD_MB:
                                st.session_state.last_large_download_time = time.time()
                            else:
                                st.session_state.last_download_time = time.time()
                            
                            if st.session_state.is_admin:
                                st.success(f"✅ تم عبر Bot API ({file_size_mb:.1f} MB)")
                        else:
                            st.error("فشل التحميل")
                            return None, None
                    else:
                        st.error("تعذر الوصول للملف")
                        return None, None
                except Exception as e:
                    st.error("حدث خطأ في الاتصال")
                    if st.session_state.is_admin: st.error(f"🔧 {str(e)}")
                    return None, None

        if file_data:
            st.session_state.downloads_count += 1
            if not file_name.endswith(f'.{file_ext}'): 
                file_name = f"{file_name}.{file_ext}"
            return file_data, file_name
        else:
            st.error("لم يتم استرجاع الملف")
            return None, None
            
    except Exception as e:
        st.error("حدث خطأ غير متوقع")
        if st.session_state.is_admin: st.error(f"🔧 {str(e)}")
        return None, None
    finally:
        st.session_state.downloading_now = False

# ═══════════════════════════════════════════════════════════════
# 🃏 عرض البطاقات (UI)
# ═══════════════════════════════════════════════════════════════

def render_book_card_clean(row):
    """عرض الكتاب بشكل نظيف تماماً"""
    file_size_mb = row.get('size_mb', 0)
    file_ext = row.get('file_extension', 'pdf').replace('.', '')
    pages = row.get('pages', '?')
    desc = row.get('description', '')
    
    # تنظيف الوصف من الروابط
    desc = re.sub(r'http\S+', '', desc)
    desc = re.sub(r'@\w+', '', desc)
    
    # تحديد إمكانية التحميل (خلفياً)
    can_download = True
    if file_size_mb > USER_SESSION_MAX_SIZE_MB:
        can_download = False
    elif file_size_mb >= 20 and not USER_SESSION_AVAILABLE:
        can_download = False
    
    st.markdown(f"""
    <div class="book-card">
        <div class="book-title">📖 {row.get('file_name', 'بدون عنوان')}</div>
        <div class="book-meta">
            <span class="meta-item" style="color: #0e7490; background: #cffafe;">📂 {file_ext.upper()}</span>
            <span class="meta-item">💾 {file_size_mb:.2f} MB</span>
            <span class="meta-item">📄 {pages} صفحة</span>
        </div>
        {f'<div class="book-desc">{desc[:250]}...</div>' if desc else ''}
    </div>
    """, unsafe_allow_html=True)
    
    # أزرار التحميل والمعاينة
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if not can_download:
            st.button("⚠️ غير متاح", key=f"btn_{row['id']}", disabled=True, use_container_width=True)
            if st.session_state.is_admin:
                if file_size_mb > USER_SESSION_MAX_SIZE_MB:
                    st.caption(f"🔧 كبير جداً ({file_size_mb:.0f} MB)")
                else:
                    st.caption("🔧 يتطلب User Session")
        else:
            if st.button("⬇️ تحميل", key=f"btn_{row['id']}", use_container_width=True, type="primary"):
                data, name = unified_downloader(row['file_id'], row['file_name'], file_size_mb, file_ext)
                
                if data and name:
                    st.download_button(
                        label="💾 حفظ الملف",
                        data=data,
                        file_name=name,
                        mime='application/octet-stream',
                        key=f"dl_{row['id']}",
                        use_container_width=True
                    )
                    st.balloons()
    
    with col2:
        if file_ext.lower() in ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx']:
            if st.button("👁️ معاينة", key=f"view_{row['id']}", use_container_width=True):
                preview_link = get_telegram_file_url(row['file_id'])
                
                if preview_link:
                    viewer_url = f"https://docs.google.com/viewer?url={preview_link}&embedded=true"
                    st.markdown(f"""
                    <a href="{viewer_url}" target="_blank" style="
                        display: inline-block;
                        padding: 0.5rem 1rem;
                        background: #0e7490;
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                        font-weight: 600;
                        margin-top: 0.5rem;
                    ">🔗 فتح المعاينة</a>
                    """, unsafe_allow_html=True)
                else:
                    st.info("المعاينة غير متاحة")

# ═══════════════════════════════════════════════════════════════
# 🖥️ واجهة التطبيق الرئيسية
# ═══════════════════════════════════════════════════════════════

# تحميل القاعدة بصمت
if not st.session_state.db_loaded:
    download_db_from_gdrive()

# إدارة الجلسات بصمت
current_time = time.time()
for sid in list(st.session_state.active_sessions.keys()):
    if current_time - st.session_state.active_sessions[sid]['start_time'] > SESSION_TIMEOUT:
        del st.session_state.active_sessions[sid]

active_count = len(st.session_state.active_sessions)
max_allowed = 15

# الشريط العلوي
st.markdown(f"""
<div class="toolbar">
    <div class="app-title">🏛️ المكتبة الرقمية</div>
    <div style="display: flex; gap: 10px; align-items: center;">
        {f'<span class="status-active">👑 مشرف النظام</span>' if st.session_state.is_admin else ''}
        {f'<span style="color:#0e7490; font-weight:bold; font-size:0.9rem;">الزوار: {active_count}</span>' if st.session_state.show_counter else ''}
    </div>
</div>
<div style="margin-top: 90px;"></div>
""", unsafe_allow_html=True)

# صفحة الدخول (غرفة الانتظار)
if not st.session_state.session_id and not st.session_state.is_admin:
    can_enter = active_count < max_allowed
    
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem;">
        <h1 style="color: #1e293b; font-size: 2.5rem; margin-bottom: 1rem;">مرحباً بك في المكتبة الرقمية</h1>
        <p style="color: #64748b; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
            مكتبة شاملة تضم آلاف الكتب والمراجع. ابحث، تصفح، وحمل الكتب بسهولة وسرعة فائقة.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
        if can_enter:
            if st.button("🚀 الدخول للمكتبة", use_container_width=True, type="primary"):
                sid = hashlib.md5(f"{time.time()}".encode()).hexdigest()[:10]
                st.session_state.active_sessions[sid] = {'start_time': time.time()}
                st.session_state.session_id = sid
                st.session_state.session_start_time = time.time()
                st.rerun()
        else:
            st.warning("⚠️ المكتبة مزدحمة حالياً، يرجى الانتظار قليلاً...")
            time.sleep(5)
            st.rerun()
            
    with st.expander("🔒 دخول الإدارة"):
        if st.text_input("كلمة المرور", type="password") == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()

# واجهة المكتبة (بعد الدخول)
else:
    if st.session_state.session_id:
        elapsed = int(current_time - st.session_state.session_start_time)
        remaining = max(0, SESSION_TIMEOUT - elapsed)
        if remaining == 0:
            st.session_state.session_id = None
            st.rerun()
        st.progress(remaining / SESSION_TIMEOUT)
    
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        query = st.text_input("", placeholder="🔍 ابحث عن كتاب، مؤلف، أو موضوع...", label_visibility="collapsed")
    with col_btn:
        do_search = st.button("بحث", use_container_width=True, type="primary")

    if query or do_search:
        with st.spinner("جاري البحث في الأرفف..."):
            results = search_books_advanced(query, limit=30)
        
        if results:
            st.success(f"تم العثور على {len(results)} كتاب")
            for row in results:
                render_book_card_clean(row)
        else:
            st.info("لم يتم العثور على نتائج مطابقة.")

    if st.session_state.is_admin:
        with st.expander("🛠️ لوحة تحكم النظام", expanded=False):
            st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
            
            st.write("**📊 إحصائيات:**")
            st.write(f"- الجلسات النشطة: {len(st.session_state.active_sessions)}")
            st.write(f"- تحميلات Bot: {st.session_state.downloads_count}")
            st.write(f"- تحميلات User Session: {st.session_state.user_session_downloads_count}")
            st.write(f"- حجم القاعدة: {st.session_state.db_size:.2f} MB")
            
            st.write(f"\n**🔧 الحدود:**")
            st.write(f"- Bot API: 0-20 MB")
            st.write(f"- User Session: 20-2000 MB ({'✅ متاح' if USER_SESSION_AVAILABLE else '❌ غير متاح'})")
            
            st.divider()
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🧹 تصفير الجلسات", use_container_width=True):
                    st.session_state.active_sessions = {}
                    st.success("✅ تم")
            
            with col_b:
                if st.button("🚪 خروج", use_container_width=True):
                    st.session_state.is_admin = False
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
    if st.session_state.session_id:
        if st.button("خروج من المكتبة"):
            del st.session_state.active_sessions[st.session_state.session_id]
            st.session_state.session_id = None
            st.rerun()