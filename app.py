import streamlit as st
import sqlite3
import requests
import time
import os
import shutil
import html
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

# تحسين CSS (تم وضعه في سطر واحد لتجنب المشاكل)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
*{font-family:'Cairo',sans-serif;}
#MainMenu{visibility:hidden;}footer{visibility:hidden;}header{visibility:hidden;}
.stApp{background-color:#f8f9fa;}
.toolbar-container{position:fixed;top:0;left:0;right:0;background:white;padding:0.8rem 2rem;display:flex;justify-content:space-between;align-items:center;box-shadow:0 4px 20px rgba(0,0,0,0.05);z-index:99999;direction:rtl;border-bottom:3px solid #0e7490;}
.app-title{color:#0e7490;font-weight:700;font-size:1.4rem;display:flex;align-items:center;gap:10px;}
.book-card{background:white;border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;border:1px solid #e5e7eb;box-shadow:0 2px 5px rgba(0,0,0,0.02);transition:transform 0.2s,box-shadow 0.2s;direction:rtl;position:relative;overflow:hidden;}
.book-card:hover{transform:translateY(-2px);box-shadow:0 10px 25px rgba(14,116,144,0.1);border-color:#0e7490;}
.book-card::before{content:'';position:absolute;right:0;top:0;bottom:0;width:6px;background:#0e7490;border-radius:0 4px 4px 0;}
.book-title{font-size:1.3rem;font-weight:700;color:#1f2937;margin-bottom:0.8rem;}
.book-meta{display:flex;gap:1rem;align-items:center;color:#6b7280;font-size:0.9rem;margin-bottom:1rem;flex-wrap:wrap;}
.meta-item{background:#f3f4f6;padding:0.2rem 0.8rem;border-radius:8px;display:flex;align-items:center;gap:5px;}
.book-desc{color:#4b5563;font-size:0.95rem;line-height:1.7;padding-top:1rem;border-top:1px dashed #e5e7eb;margin-top:0.5rem;white-space:pre-wrap;}
.status-active{background:#ecfdf5;color:#047857;padding:0.5rem 1rem;border-radius:12px;font-weight:600;font-size:0.9rem;border:1px solid #a7f3d0;}
.admin-panel{background:#fffbeb;border:2px solid #fbbf24;padding:1.5rem;border-radius:12px;margin:2rem 0;direction:rtl;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# ⚙️ الإعدادات (Backend)
# ═══════════════════════════════════════════════════════════════

try:
    BOT_TOKENS = [st.secrets["bot1"], st.secrets["bot2"], st.secrets["bot3"]]
    CHANNEL_ID = st.secrets["channelid"]
    ADMIN_PASSWORD = st.secrets["password"]
    USER_API_ID = st.secrets.get("user_api_id", "")
    USER_API_HASH = st.secrets.get("user_api_hash", "")
    USER_SESSION_STRING = st.secrets.get("user_session_string", "")
    
    if "db_parts" in st.secrets:
        DB_PARTS = dict(st.secrets["db_parts"])
    else:
        st.error("⚠️ لم يتم العثور على قسم [db_parts] في أسرار Streamlit")
        st.stop()
        
except Exception as e:
    st.error(f"⚠️ خطأ في إعدادات النظام الداخلي (Secrets): {e}")
    st.stop()

DATABASE_FILE = "/tmp/books_merged.db"
DB_TEMP_DIR = "/tmp/db_parts"
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
# 🛠️ دوال التحميل المباشر
# ═══════════════════════════════════════════════════════════════

def download_specific_files(file_map, output_dir):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded_files = []
    progress_text = st.empty()
    
    for i, (filename, url) in enumerate(file_map.items()):
        if not filename.endswith('.db'): filename += ".db"
        output_path = os.path.join(output_dir, filename)
        
        progress_text.info(f"⏳ جاري تحميل الجزء {i+1} من {len(file_map)}...")
        
        try:
            response = requests.get(url, stream=True, timeout=60)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                if os.path.exists(output_path):
                    with open(output_path, 'rb') as f:
                        header = f.read(16)
                        if b'SQLite format 3' in header:
                            downloaded_files.append(output_path)
                            st.toast(f"✅ تم تحميل {filename}")
                        else:
                            st.error(f"❌ الملف {filename} تم تحميله لكنه ليس قاعدة بيانات.")
            else:
                st.error(f"❌ فشل تحميل {filename} (HTTP {response.status_code})")
        except Exception as e:
            st.error(f"❌ خطأ في الاتصال أثناء تحميل {filename}: {e}")
            
    progress_text.empty()
    return downloaded_files

def merge_databases(db_files, output_file):
    try:
        merged_conn = sqlite3.connect(output_file)
        merged_cursor = merged_conn.cursor()
        
        merged_cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                description TEXT,
                file_id TEXT,
                message_id INTEGER,
                size_mb REAL,
                pages INTEGER,
                file_extension TEXT,
                normalized_name TEXT,
                normalized_desc TEXT,
                date_added TEXT
            )
        """)
        
        files_merged = 0
        total_records = 0
        
        for db_file in db_files:
            try:
                source_conn = sqlite3.connect(db_file)
                source_cursor = source_conn.cursor()
                source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books'")
                if not source_cursor.fetchone():
                    source_conn.close()
                    continue
                source_cursor.execute("SELECT * FROM books")
                columns = [description[0] for description in source_cursor.description]
                placeholders = ','.join(['?' for _ in columns])
                insert_sql = f"INSERT INTO books ({','.join(columns)}) VALUES ({placeholders})"
                rows = source_cursor.fetchall()
                for row in rows:
                    try:
                        merged_cursor.execute(insert_sql, row)
                        total_records += 1
                    except sqlite3.IntegrityError:
                        continue 
                source_conn.close()
                files_merged += 1
            except Exception:
                continue
        merged_conn.commit()
        merged_conn.close()
        return files_merged, total_records
    except Exception as e:
        st.error(f"خطأ في دمج القواعد: {e}")
        return 0, 0

def init_db():
    if os.path.exists(DATABASE_FILE) and os.path.getsize(DATABASE_FILE) > 102400:
        if time.time() - os.path.getmtime(DATABASE_FILE) < DB_CACHE_TIME:
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                conn.cursor().execute("SELECT count(*) FROM books")
                conn.close()
                st.session_state.db_loaded = True
                st.session_state.db_size = os.path.getsize(DATABASE_FILE) / (1024 * 1024)
                return True
            except:
                pass 

    if not DB_PARTS:
        st.error("⚠️ قائمة الملفات فارغة في الأسرار.")
        return False

    with st.spinner("📦 جاري بناء المكتبة من المصدر..."):
        db_files = download_specific_files(DB_PARTS, DB_TEMP_DIR)
        if not db_files:
            st.error("❌ فشل تحميل ملفات قاعدة البيانات.")
            return False
        files_merged, total_records = merge_databases(db_files, DATABASE_FILE)
        if files_merged > 0:
            st.session_state.db_loaded = True
            st.session_state.db_last_update = time.time()
            st.session_state.db_size = os.path.getsize(DATABASE_FILE) / (1024 * 1024)
            try: shutil.rmtree(DB_TEMP_DIR)
            except: pass
            st.success(f"✅ تم تجهيز المكتبة: {total_records} كتاب متاح.")
            time.sleep(1)
            st.rerun()
            return True
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
# 🔍 البحث الذكي
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
        if 'description' in existing_columns and 'normalized_desc' not in existing_columns: search_targets.append('description')
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
        if st.session_state.get('is_admin', False): st.error(f"Error: {e}")
        try:
            cursor.execute(f"SELECT * FROM books WHERE file_name LIKE ? LIMIT ?", (f'%{query}%', limit))
            return [dict(r) for r in cursor.fetchall()]
        except: return []

# ═══════════════════════════════════════════════════════════════
# 📥 منطق التحميل الموحد (المُعدَّل الكامل)
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

def download_via_bot(file_id, file_name):
    """
    التحميل باستخدام Bot API مع إعادة محاولة ذكية
    """
    try:
        bot_token = get_best_bot()
        
        with st.spinner(f"📥 البوت يحمّل: {file_name[:30]}..."):
            # الحصول على معلومات الملف
            file_info_url = f"https://api.telegram.org/bot{bot_token}/getFile"
            response = requests.get(file_info_url, params={"file_id": file_id}, timeout=30)
            
            if response.status_code != 200:
                if st.session_state.get('is_admin'):
                    st.warning(f"⚠️ Bot getFile فشل: HTTP {response.status_code}")
                return None
            
            result = response.json()
            if not result.get("ok"):
                if st.session_state.get('is_admin'):
                    st.warning(f"⚠️ Bot Error: {result.get('description', 'Unknown')}")
                return None
            
            file_path = result.get("result", {}).get("file_path")
            if not file_path:
                return None
            
            # تحميل الملف
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            file_response = requests.get(download_url, stream=True, timeout=90)
            
            if file_response.status_code == 200:
                file_data = io.BytesIO()
                total_size = 0
                for chunk in file_response.iter_content(chunk_size=8192):
                    file_data.write(chunk)
                    total_size += len(chunk)
                
                if total_size > 100:  # تأكد أن الملف ليس فارغاً
                    return file_data.getvalue()
        
        return None
    
    except Exception as e:
        if st.session_state.get('is_admin'):
            st.warning(f"⚠️ Bot Exception: {str(e)[:100]}")
        return None

def download_via_telethon(message_id, file_name):
    """
    التحميل باستخدام Telethon User Session مع retry
    """
    if not USER_SESSION_AVAILABLE:
        return None
    
    try:
        from telethon.sync import TelegramClient
        from telethon.sessions import StringSession
        
        with st.spinner(f"☁️ Telethon يحمّل: {file_name[:30]}..."):
            client = TelegramClient(
                StringSession(USER_SESSION_STRING),
                USER_API_ID,
                USER_API_HASH
            )
            
            with client:
                message = client.get_messages(CHANNEL_ID, ids=int(message_id))
                
                if not message or not message.media:
                    if st.session_state.get('is_admin'):
                        st.warning(f"⚠️ Telethon: رسالة {message_id} لا تحتوي ملف")
                    return None
                
                file_buffer = io.BytesIO()
                client.download_media(message, file=file_buffer)
                
                file_data = file_buffer.getvalue()
                if len(file_data) > 100:  # تأكد أن الملف ليس فارغاً
                    return file_data
        
        return None
    
    except Exception as e:
        if st.session_state.get('is_admin'):
            st.error(f"❌ Telethon فشل: {str(e)[:100]}")
        return None

def unified_downloader(message_id, file_name, file_size_mb, file_ext, file_id=None):
    """
    التحميل الموحد مع توزيع ذكي لتجنب الحظر
    
    استراتيجية التوزيع:
    - ملفات صغيرة (<2MB): Bot فقط (70% Bot، 30% Telethon للتنويع)
    - ملفات متوسطة (2-10MB): Bot أولاً ثم Telethon
    - ملفات كبيرة (10-20MB): Telethon مع محاولة Bot
    - ملفات ضخمة (>20MB): Telethon فقط
    """
    if st.session_state.downloading_now:
        st.warning("⏳ انتظر انتهاء التحميل الحالي...")
        return None
    
    can_download, wait_time, method = check_cooldowns(file_size_mb)
    
    if not can_download:
        if method == "unavailable":
            st.error("❌ الملف كبير جداً - تحتاج جلسة مستخدم مفعّلة")
            return None
        
        msg_holder = st.empty()
        for i in range(int(wait_time), 0, -1):
            msg_holder.info(f"🔄 انتظر {i} ثواني لتجنب الحظر...")
            time.sleep(1)
        msg_holder.empty()
    
    st.session_state.downloading_now = True
    
    try:
        file_data = None
        download_method_used = None
        
        # ═══════════════════════════════════════════════════════
        # استراتيجية التوزيع الذكي
        # ═══════════════════════════════════════════════════════
        
        # 1️⃣ ملفات ضخمة (>20MB) - Telethon فقط
        if file_size_mb > 20:
            if not USER_SESSION_AVAILABLE:
                st.error("❌ جلسة المستخدم مطلوبة للملفات الكبيرة")
                return None
            
            file_data = download_via_telethon(message_id, file_name)
            download_method_used = "telethon"
            if file_data:
                st.session_state.last_user_session_download = time.time()
                st.session_state.user_session_downloads_count += 1
        
        # 2️⃣ ملفات كبيرة (10-20MB) - Telethon أولاً
        elif file_size_mb > 10:
            # نحاول Telethon أولاً للملفات الكبيرة
            if USER_SESSION_AVAILABLE:
                file_data = download_via_telethon(message_id, file_name)
                download_method_used = "telethon"
                if file_data:
                    st.session_state.last_user_session_download = time.time()
                    st.session_state.user_session_downloads_count += 1
            
            # إذا فشل Telethon أو غير متاح، نجرب Bot
            if not file_data and file_id:
                file_data = download_via_bot(file_id, file_name)
                download_method_used = "bot"
                if file_data:
                    st.session_state.last_large_download_time = time.time()
        
        # 3️⃣ ملفات متوسطة (2-10MB) - Bot أولاً ثم Telethon
        elif file_size_mb > 2:
            # نحاول Bot أولاً
            if file_id:
                file_data = download_via_bot(file_id, file_name)
                download_method_used = "bot"
                if file_data:
                    st.session_state.last_large_download_time = time.time()
            
            # إذا فشل Bot، نجرب Telethon
            if not file_data and USER_SESSION_AVAILABLE:
                file_data = download_via_telethon(message_id, file_name)
                download_method_used = "telethon"
                if file_data:
                    st.session_state.user_session_downloads_count += 1
        
        # 4️⃣ ملفات صغيرة (<2MB) - توزيع 70% Bot / 30% Telethon
        else:
            # توزيع عشوائي لتقليل الضغط
            use_bot_first = (st.session_state.downloads_count % 10) < 7  # 70% Bot
            
            if use_bot_first and file_id:
                file_data = download_via_bot(file_id, file_name)
                download_method_used = "bot"
                if file_data:
                    st.session_state.last_download_time = time.time()
                
                # إذا فشل Bot، نجرب Telethon
                if not file_data and USER_SESSION_AVAILABLE:
                    file_data = download_via_telethon(message_id, file_name)
                    download_method_used = "telethon"
                    if file_data:
                        st.session_state.user_session_downloads_count += 1
            
            elif USER_SESSION_AVAILABLE:
                file_data = download_via_telethon(message_id, file_name)
                download_method_used = "telethon"
                if file_data:
                    st.session_state.user_session_downloads_count += 1
                
                # إذا فشل Telethon، نجرب Bot
                if not file_data and file_id:
                    file_data = download_via_bot(file_id, file_name)
                    download_method_used = "bot"
                    if file_data:
                        st.session_state.last_download_time = time.time()
            
            # آخر محاولة: Bot فقط
            elif file_id:
                file_data = download_via_bot(file_id, file_name)
                download_method_used = "bot"
                if file_data:
                    st.session_state.last_download_time = time.time()
        
        # ═══════════════════════════════════════════════════════
        # المعالجة النهائية
        # ═══════════════════════════════════════════════════════
        
        if file_data:
            st.session_state.downloads_count += 1
            if not file_name.endswith(f'.{file_ext}'):
                file_name = f"{file_name}.{file_ext}"
            
            # عرض طريقة التحميل للمشرف
            if st.session_state.get('is_admin') and download_method_used:
                st.success(f"✅ تم عبر: {download_method_used.upper()}")
            
            return file_data, file_name
        else:
            st.error("❌ فشل التحميل من جميع المصادر - تحقق من file_id أو message_id")
            if st.session_state.get('is_admin'):
                st.info(f"🔍 Debug: file_id={file_id}, message_id={message_id}, size={file_size_mb}MB")
            return None
    
    except Exception as e:
        st.error(f"❌ خطأ غير متوقع: {str(e)[:150]}")
        return None
    
    finally:
        st.session_state.downloading_now = False

# ═══════════════════════════════════════════════════════════════
# 🖥️ الواجهة والعرض
# ═══════════════════════════════════════════════════════════════

def render_book_card_clean(row):
    """
    نسخة مضغوطة (Minified) لمنع أي تفسير خاطئ للأكواد
    """
    file_size_mb = row.get('size_mb', 0)
    file_ext = row.get('file_extension', 'pdf').replace('.', '')
    pages = row.get('pages')
    
    pages_html = ""
    if pages and str(pages).isdigit() and int(pages) > 0:
        pages_html = f'<span class="meta-item">📄 {pages} صفحة</span>'

    desc = row.get('description', '')
    desc_html = ""
    if desc:
        desc = re.sub(r'http\S+', '', desc)
        desc = re.sub(r'@\w+', '', desc)
        safe_desc = html.escape(desc[:250])
        desc_html = f'<div class="book-desc">{safe_desc}...</div>'

    card_html = f"""<div class="book-card"><div class="book-title">📖 {row.get('file_name', 'بدون عنوان')}</div><div class="book-meta"><span class="meta-item" style="color: #0e7490; background: #cffafe;">📂 {file_ext.upper()}</span><span class="meta-item">💾 {file_size_mb:.2f} MB</span>{pages_html}</div>{desc_html}</div>"""
    
    st.markdown(card_html, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if file_size_mb > USER_SESSION_MAX_SIZE_MB:
            st.warning("⚠️ كبير جداً")
        else:
            if st.button("⬇️ تحميل", key=f"btn_{row['id']}", use_container_width=True, type="primary"):
                result = unified_downloader(
                    row['message_id'], 
                    row['file_name'], 
                    file_size_mb, 
                    file_ext,
                    row.get('file_id')
                )
                if result:
                    data, name = result
                    st.download_button("💾 حفظ", data, name, mime='application/octet-stream', key=f"dl_{row['id']}", use_container_width=True)
                    st.balloons()

# التحميل الصامت
if not st.session_state.db_loaded: init_db()

# تنظيف الجلسات
current_time = time.time()
for sid in list(st.session_state.active_sessions.keys()):
    if current_time - st.session_state.active_sessions[sid]['start_time'] > SESSION_TIMEOUT:
        del st.session_state.active_sessions[sid]

active_count = len(st.session_state.active_sessions)
max_allowed = 15

# الشريط العلوي
admin_badge = '<span class="status-active">👑 مشرف</span>' if st.session_state.is_admin else ''
visitor_badge = f'<span style="color:#0e7490; font-weight:bold;">الزوار: {active_count}</span>' if st.session_state.show_counter else ''
toolbar_html = f"""<div class="toolbar-container"><div class="app-title">🏛️ المكتبة الرقمية</div><div style="display: flex; gap: 10px; align-items: center;">{admin_badge}{visitor_badge}</div></div><div style="margin-top: 90px;"></div>"""

st.markdown(toolbar_html, unsafe_allow_html=True)

if not st.session_state.session_id and not st.session_state.is_admin:
    st.markdown("""<div style="text-align: center; margin-top: 3rem;"><h1 style="color: #1e293b; font-size: 2.5rem; margin-bottom: 1rem;">مرحباً بك في المكتبة الرقمية</h1></div>""", unsafe_allow_html=True)
    
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
                db_size = st.session_state.db_size
                st.warning(f"تشخيص المشرف: حجم القاعدة المحملة {db_size:.2f} MB.")

    if st.session_state.is_admin:
        with st.expander("🛠️ التحكم", expanded=False):
            st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
            
            # الإحصائيات
            st.write("### 📊 الإحصائيات")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("الجلسات النشطة", len(st.session_state.active_sessions))
                st.metric("حجم القاعدة", f"{st.session_state.db_size:.2f} MB")
            with col2:
                st.metric("إجمالي التحميلات", st.session_state.downloads_count)
                bot_downloads = st.session_state.downloads_count - st.session_state.user_session_downloads_count
                st.metric("تحميلات البوت", bot_downloads)
                st.metric("تحميلات Telethon", st.session_state.user_session_downloads_count)
            
            # نسبة التوزيع
            if st.session_state.downloads_count > 0:
                bot_percentage = (bot_downloads / st.session_state.downloads_count) * 100
                tel_percentage = (st.session_state.user_session_downloads_count / st.session_state.downloads_count) * 100
                st.progress(bot_percentage / 100, text=f"🤖 Bot: {bot_percentage:.1f}%")
                st.progress(tel_percentage / 100, text=f"☁️ Telethon: {tel_percentage:.1f}%")
            
            st.write("---")
            
            # اختبار الاتصال
            st.write("### 🧪 اختبار النظام")
            
            test_col1, test_col2 = st.columns(2)
            
            with test_col1:
                if st.button("🤖 اختبار البوتات", use_container_width=True):
                    st.write("جاري اختبار البوتات...")
                    working_bots = 0
                    for i, token in enumerate(BOT_TOKENS):
                        try:
                            test_url = f"https://api.telegram.org/bot{token}/getMe"
                            response = requests.get(test_url, timeout=10)
                            if response.status_code == 200 and response.json().get("ok"):
                                bot_name = response.json().get("result", {}).get("first_name", f"Bot {i+1}")
                                st.success(f"✅ Bot {i+1}: {bot_name}")
                                working_bots += 1
                            else:
                                st.error(f"❌ Bot {i+1}: فشل")
                        except Exception as e:
                            st.error(f"❌ Bot {i+1}: {str(e)[:50]}")
                    
                    if working_bots == len(BOT_TOKENS):
                        st.balloons()
                        st.success(f"🎉 جميع البوتات تعمل ({working_bots}/{len(BOT_TOKENS)})")
                    else:
                        st.warning(f"⚠️ {working_bots}/{len(BOT_TOKENS)} بوتات تعمل")
            
            with test_col2:
                if st.button("☁️ اختبار Telethon", use_container_width=True):
                    if not USER_SESSION_AVAILABLE:
                        st.error("❌ Telethon غير مفعّل في Secrets")
                    else:
                        try:
                            from telethon.sync import TelegramClient
                            from telethon.sessions import StringSession
                            
                            st.write("جاري اختبار Telethon...")
                            
                            with st.spinner("الاتصال..."):
                                client = TelegramClient(
                                    StringSession(USER_SESSION_STRING),
                                    USER_API_ID,
                                    USER_API_HASH
                                )
                                
                                with client:
                                    me = client.get_me()
                                    channel = client.get_entity(CHANNEL_ID)
                                    
                                    st.success(f"✅ متصل كـ: {me.first_name}")
                                    st.success(f"✅ القناة: {channel.title}")
                                    st.balloons()
                        
                        except Exception as e:
                            st.error(f"❌ فشل: {str(e)[:100]}")
            
            st.write("---")
            
            # أوامر الإدارة
            st.write("### ⚙️ أوامر الإدارة")
            
            admin_col1, admin_col2, admin_col3 = st.columns(3)
            
            with admin_col1:
                if st.button("🔄 تصفير الجلسات", use_container_width=True):
                    st.session_state.active_sessions = {}
                    st.success("✅ تم تصفير الجلسات")
                    st.rerun()
            
            with admin_col2:
                if st.button("📊 تصفير الإحصائيات", use_container_width=True):
                    st.session_state.downloads_count = 0
                    st.session_state.user_session_downloads_count = 0
                    st.success("✅ تم تصفير الإحصائيات")
                    st.rerun()
            
            with admin_col3:
                if st.button("🔃 إعادة تحميل القاعدة", use_container_width=True):
                    try: 
                        if os.path.exists(DATABASE_FILE):
                            os.remove(DATABASE_FILE)
                        if os.path.exists(DB_TEMP_DIR):
                            shutil.rmtree(DB_TEMP_DIR)
                    except: 
                        pass
                    st.session_state.db_loaded = False
                    st.success("✅ سيتم إعادة التحميل...")
                    time.sleep(1)
                    st.rerun()
            
            if st.button("🚪 خروج المشرف", use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
    if st.session_state.session_id:
        if st.button("خروج"):
            del st.session_state.active_sessions[st.session_state.session_id]
            st.session_state.session_id = None
            st.rerun()