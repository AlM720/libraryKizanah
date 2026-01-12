import streamlit as st
import sqlite3
import requests
import time
import os
import gdown
from datetime import datetime, timedelta
import hashlib
import re
import io

# ═══════════════════════════════════════════════════════════════
# 🎨 إعدادات الصفحة والتصميم
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="المكتبة الرقمية الشاملة",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    * {font-family: 'Cairo', sans-serif;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {background-color: #f8f9fa;}
    .toolbar {
        position: fixed; top: 0; left: 0; right: 0;
        background: white; padding: 0.8rem 2rem;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        z-index: 1000; direction: rtl; border-bottom: 3px solid #0e7490;
    }
    .app-title {color: #0e7490; font-weight: 700; font-size: 1.4rem; display: flex; align-items: center; gap: 10px;}
    .book-card {
        background: white; border-radius: 16px; padding: 1.5rem;
        margin-bottom: 1.5rem; border: 1px solid #e5e7eb;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        transition: transform 0.2s, box-shadow 0.2s;
        direction: rtl; position: relative; overflow: hidden;
    }
    .book-card:hover {transform: translateY(-2px); box-shadow: 0 10px 25px rgba(14, 116, 144, 0.1); border-color: #0e7490;}
    .book-card::before {content: ''; position: absolute; right: 0; top: 0; bottom: 0; width: 6px; background: #0e7490; border-radius: 0 4px 4px 0;}
    .book-title {font-size: 1.3rem; font-weight: 700; color: #1f2937; margin-bottom: 0.8rem;}
    .book-meta {display: flex; gap: 1rem; align-items: center; color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem; flex-wrap: wrap;}
    .meta-item {background: #f3f4f6; padding: 0.2rem 0.8rem; border-radius: 8px; display: flex; align-items: center; gap: 5px;}
    .book-desc {color: #4b5563; font-size: 0.95rem; line-height: 1.7; padding-top: 1rem; border-top: 1px dashed #e5e7eb; margin-top: 0.5rem;}
    .status-active {background: #ecfdf5; color: #047857; padding: 0.5rem 1rem; border-radius: 12px; font-weight: 600; font-size: 0.9rem; border: 1px solid #a7f3d0;}
    .admin-panel {background: #fffbeb; border: 2px solid #fbbf24; padding: 1.5rem; border-radius: 12px; margin: 2rem 0; direction: rtl;}
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
DB_CACHE_TIME = 3600
SESSION_TIMEOUT = 600
MIN_REQUEST_INTERVAL = 3
MAX_REQUESTS_PER_MINUTE = 15
LARGE_FILE_MIN_INTERVAL = 8
LARGE_FILE_THRESHOLD_MB = 5
USER_SESSION_MIN_INTERVAL = 10
USER_SESSION_MAX_SIZE_MB = 2000

# ═══════════════════════════════════════════════════════════════
# 📦 إدارة الحالة
# ═══════════════════════════════════════════════════════════════

for key in ['active_sessions', 'bot_requests', 'session_id', 'is_admin', 'show_counter', 
            'db_loaded', 'db_last_update', 'db_size', 'downloading_now', 
            'last_download_time', 'last_large_download_time', 
            'last_user_session_download', 'user_session_downloads_count', 'downloads_count']:
    if key not in st.session_state:
        if key == 'bot_requests': st.session_state[key] = {i: [] for i in range(len(BOT_TOKENS))}
        elif key == 'active_sessions': st.session_state[key] = {}
        elif key in ['show_counter', 'is_admin', 'db_loaded', 'downloading_now']: st.session_state[key] = False
        elif key in ['db_last_update', 'db_size', 'user_session_downloads_count', 'downloads_count']: st.session_state[key] = 0
        else: st.session_state[key] = 0.0

USER_SESSION_AVAILABLE = bool(USER_API_ID and USER_API_HASH and USER_SESSION_STRING)

# ═══════════════════════════════════════════════════════════════
# 🛠️ الدوال المساعدة وتحميل القاعدة (Gdown)
# ═══════════════════════════════════════════════════════════════

def extract_file_id(url_or_id):
    if not url_or_id: return None
    if len(url_or_id) < 50 and '/' not in url_or_id: return url_or_id
    patterns = [r'/file/d/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)', r'/folders/([a-zA-Z0-9_-]+)']
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match: return match.group(1)
    return url_or_id

def init_db():
    if not GDRIVE_FILE_ID: return False
    
    # التحقق من وجود الملف وصلاحيته
    if os.path.exists(DATABASE_FILE):
        if os.path.getsize(DATABASE_FILE) < 102400: # 100KB
            try: os.remove(DATABASE_FILE)
            except: pass
        elif time.time() - os.path.getmtime(DATABASE_FILE) < DB_CACHE_TIME:
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                conn.execute("SELECT 1 FROM books LIMIT 1")
                conn.close()
                st.session_state.db_loaded = True
                st.session_state.db_size = os.path.getsize(DATABASE_FILE) / (1024 * 1024)
                return True
            except:
                try: os.remove(DATABASE_FILE)
                except: pass

    # التحميل باستخدام gdown (الحل الجذري)
    try:
        file_id = extract_file_id(GDRIVE_FILE_ID)
        url = f'https://drive.google.com/uc?id={file_id}'
        
        with st.spinner("📦 جاري تحميل قاعدة البيانات الكبيرة..."):
            # quiet=False لإظهار الأخطاء في الكونسول، fuzzy=True لتخمين الاسم
            output = gdown.download(url, DATABASE_FILE, quiet=False, fuzzy=True)
        
        if output and os.path.exists(DATABASE_FILE):
            final_size = os.path.getsize(DATABASE_FILE)
            if final_size > 102400: # أكبر من 100KB
                st.session_state.db_loaded = True
                st.session_state.db_last_update = time.time()
                st.session_state.db_size = final_size / (1024 * 1024)
                return True
        
        return False
    except Exception as e:
        st.error(f"حدث خطأ أثناء تحميل القاعدة: {e}")
        return False

def get_db_connection():
    if not st.session_state.db_loaded:
        if not init_db(): return None
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except: return None

# ═══════════════════════════════════════════════════════════════
# 🔍 البحث الذكي (Adaptive Search)
# ═══════════════════════════════════════════════════════════════

def normalize_arabic_text(text):
    if not text: return ""
    text = re.sub(r'[^\w\s]', ' ', text)
    return ' '.join(text.split()).strip().lower()

def search_books_advanced(query, filters=None, limit=50):
    if not query or len(query) < 2: return []
    filters = filters or {}
    
    clean_query = normalize_arabic_text(query)
    words = [w for w in clean_query.split() if len(w) > 1]
    if not words: return []
    
    conn = get_db_connection()
    if not conn: return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(books)")
        columns_info = cursor.fetchall()
        existing_columns = [col[1] for col in columns_info]
        
        search_targets = []
        if 'file_name' in existing_columns: search_targets.append('file_name')
        if 'normalized_name' in existing_columns: search_targets.append('normalized_name')
        if 'normalized_desc' in existing_columns: search_targets.append('normalized_desc')
        if 'description' in existing_columns and 'normalized_desc' not in existing_columns: 
            search_targets.append('description')

        if not search_targets: return []

        sql_parts, params = [], []
        for word in words:
            word_conditions = []
            for col in search_targets:
                word_conditions.append(f"{col} LIKE ?")
                params.append(f'%{word}%')
            if word_conditions:
                sql_parts.append("(" + " OR ".join(word_conditions) + ")")
            
        where = " AND ".join(sql_parts)
        
        if filters.get('format') and filters['format'] != 'all':
            if 'file_extension' in existing_columns:
                where += " AND file_extension = ?"
                params.append(filters['format'])
        
        order_clause = "message_id DESC"
        if 'normalized_name' in existing_columns:
            order_clause = "length(normalized_name) ASC, message_id DESC"
        elif 'file_name' in existing_columns:
            order_clause = "length(file_name) ASC, message_id DESC"

        sql = f"SELECT * FROM books WHERE {where} ORDER BY {order_clause} LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        results = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return results

    except Exception as e:
        if st.session_state.get('is_admin', False):
            st.error(f"Error: {e}")
        try:
            cursor.execute(f"SELECT * FROM books WHERE file_name LIKE ? LIMIT ?", (f'%{query}%', limit))
            return [dict(r) for r in cursor.fetchall()]
        except: return []

# ═══════════════════════════════════════════════════════════════
# 📥 منطق التحميل الموحد
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
    if st.session_state.downloading_now:
        st.warning("⏳ انتظر انتهاء التحميل الحالي...")
        return None

    can_download, wait_time, method = check_cooldowns(file_size_mb)
    if not can_download:
        if method == "unavailable":
            st.error("الملف غير متاح حالياً.")
            return None
        msg_holder = st.empty()
        for i in range(int(wait_time), 0, -1):
            msg_holder.info(f"🔄 يرجى الانتظار {i} ثواني...")
            time.sleep(1)
        msg_holder.empty()

    st.session_state.downloading_now = True
    try:
        file_data = None
        if method == "user_session" or (method == "bot" and file_size_mb > 20):
            if not USER_SESSION_AVAILABLE:
                st.error("خاصية التحميل الكبير غير مفعلة.")
                return None
            from telethon.sync import TelegramClient
            from telethon.sessions import StringSession
            with st.spinner("📥 جلب الملف من السحابة..."):
                try:
                    client = TelegramClient(StringSession(USER_SESSION_STRING), USER_API_ID, USER_API_HASH)
                    with client:
                        file_buffer = io.BytesIO()
                        client.download_file(file_id, file=file_buffer)
                        file_buffer.seek(0)
                        file_data = file_buffer.read()
                    st.session_state.last_user_session_download = time.time()
                    st.session_state.user_session_downloads_count += 1
                except Exception as e:
                    st.error("فشل الجلب من السحابة.")
        else:
            bot_token = get_best_bot()
            with st.spinner("📥 جاري التحميل..."):
                r = requests.get(f"https://api.telegram.org/bot{bot_token}/getFile", params={'file_id': file_id})
                if r.status_code == 200:
                    path = r.json()['result']['file_path']
                    dl_url = f"https://api.telegram.org/file/bot{bot_token}/{path}"
                    file_res = requests.get(dl_url, stream=True)
                    if file_res.status_code == 200:
                        file_data = file_res.content
                        if file_size_mb >= LARGE_FILE_THRESHOLD_MB:
                            st.session_state.last_large_download_time = time.time()
                        else:
                            st.session_state.last_download_time = time.time()

        if file_data:
            st.session_state.downloads_count += 1
            if not file_name.endswith(f'.{file_ext}'): file_name = f"{file_name}.{file_ext}"
            return file_data, file_name
        else:
            st.error("خطأ في الاتصال.")
            return None, None
    except:
        st.error("حدث خطأ غير متوقع.")
        return None, None
    finally:
        st.session_state.downloading_now = False

# ═══════════════════════════════════════════════════════════════
# 🖥️ الواجهة والعرض
# ═══════════════════════════════════════════════════════════════

def render_book_card_clean(row):
    file_size_mb = row.get('size_mb', 0)
    file_ext = row.get('file_extension', 'pdf').replace('.', '')
    pages = row.get('pages', '?')
    desc = row.get('description', '')
    desc = re.sub(r'http\S+', '', desc)
    desc = re.sub(r'@\w+', '', desc)
    
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
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if file_size_mb > USER_SESSION_MAX_SIZE_MB:
            st.warning("⚠️ كبير جداً")
        else:
            if st.button("⬇️ تحميل", key=f"btn_{row['id']}", use_container_width=True, type="primary"):
                data, name = unified_downloader(row['file_id'], row['file_name'], file_size_mb, file_ext)
                if data:
                    st.download_button("💾 حفظ", data, name, mime='application/octet-stream', key=f"dl_{row['id']}", use_container_width=True)
                    st.balloons()

# التحميل الصامت (يحدث عند فتح التطبيق)
if not st.session_state.db_loaded: init_db()

# تنظيف الجلسات
current_time = time.time()
for sid in list(st.session_state.active_sessions.keys()):
    if current_time - st.session_state.active_sessions[sid]['start_time'] > SESSION_TIMEOUT:
        del st.session_state.active_sessions[sid]

active_count = len(st.session_state.active_sessions)
max_allowed = 15

st.markdown(f"""
<div class="toolbar">
    <div class="app-title">🏛️ المكتبة الرقمية</div>
    <div style="display: flex; gap: 10px; align-items: center;">
        {f'<span class="status-active">👑 مشرف</span>' if st.session_state.is_admin else ''}
        {f'<span style="color:#0e7490; font-weight:bold;">الزوار: {active_count}</span>' if st.session_state.show_counter else ''}
    </div>
</div>
<div style="margin-top: 90px;"></div>
""", unsafe_allow_html=True)

if not st.session_state.session_id and not st.session_state.is_admin:
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem;">
        <h1 style="color: #1e293b; font-size: 2.5rem; margin-bottom: 1rem;">مرحباً بك في المكتبة الرقمية</h1>
    </div>""", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
        if active_count < max_allowed:
            if st.button("🚀 الدخول للمكتبة", use_container_width=True, type="primary"):
                sid = hashlib.md5(f"{time.time()}".encode()).hexdigest()[:10]
                st.session_state.active_sessions[sid] = {'start_time': time.time()}
                st.session_state.session_id = sid
                st.rerun()
        else:
            st.warning("⚠️ المكتبة ممتلئة...")
            time.sleep(5)
            st.rerun()
            
    with st.expander("🔒 الإدارة"):
        if st.text_input("كلمة المرور", type="password") == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()

else:
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        query = st.text_input("", placeholder="🔍 بحث...", label_visibility="collapsed")
    with col_btn:
        do_search = st.button("بحث", use_container_width=True, type="primary")

    if query or do_search:
        with st.spinner("جاري البحث..."):
            results = search_books_advanced(query, limit=30)
        if results:
            st.success(f"النتائج: {len(results)}")
            for row in results: render_book_card_clean(row)
        else:
            st.info("لم يتم العثور على نتائج.")
            if st.session_state.is_admin:
                # تشخيص للمشرف فقط
                db_size = st.session_state.db_size
                st.warning(f"تشخيص المشرف: حجم القاعدة المحملة {db_size:.2f} MB.")

    if st.session_state.is_admin:
        with st.expander("🛠️ التحكم", expanded=False):
            st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
            st.write(f"الجلسات: {len(st.session_state.active_sessions)}")
            st.write(f"حجم القاعدة: {st.session_state.db_size:.2f} MB")
            if st.button("تصفير الجلسات"):
                st.session_state.active_sessions = {}
                st.success("تم")
            if st.button("إعادة تحميل القاعدة"):
                try: os.remove(DATABASE_FILE)
                except: pass
                st.session_state.db_loaded = False
                st.rerun()
            if st.button("خروج المشرف"):
                st.session_state.is_admin = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
    if st.session_state.session_id:
        if st.button("خروج"):
            del st.session_state.active_sessions[st.session_state.session_id]
            st.session_state.session_id = None
            st.rerun()
