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

st.set_page_config(
    page_title="المكتبة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {background-color: #ffffff;}
    .toolbar {position: fixed;top: 0;left: 0;right: 0;background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);padding: 0.8rem 1rem;display: flex;justify-content: space-between;align-items: center;box-shadow: 0 2px 10px rgba(0,0,0,0.1);z-index: 1000;direction: rtl;}
    .main-title {font-size: 2.5rem;font-weight: 700;color: #667eea;margin-top: 5rem;margin-bottom: 1rem;text-align: center;}
    .result-card {background: white;border: 1px solid #e5e7eb;border-radius: 12px;padding: 1.5rem;margin: 1rem 0;box-shadow: 0 1px 3px rgba(0,0,0,0.05);transition: all 0.3s;direction: rtl;}
    .result-card:hover {box-shadow: 0 4px 12px rgba(102,126,234,0.15);border-color: #667eea;}
    .book-title {font-size: 1.2rem;font-weight: 600;color: #1f2937;margin-bottom: 0.5rem;}
    .book-meta {color: #6b7280;font-size: 0.9rem;margin: 0.5rem 0;display: flex;gap: 1rem;flex-wrap: wrap;}
    .book-description {color: #4b5563;font-size: 0.95rem;line-height: 1.6;margin: 1rem 0;padding-top: 1rem;border-top: 1px solid #e5e7eb;}
    .wait-message {max-width: 500px;margin: 6rem auto;text-align: center;padding: 2rem;background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);border-radius: 16px;border: 2px solid #667eea30;}
    .counter-badge {background: #667eea;color: white;padding: 0.3rem 0.8rem;border-radius: 20px;font-size: 0.85rem;font-weight: 600;}
    .session-info {background: #f0fdf4;border: 1px solid #86efac;padding: 1rem;border-radius: 8px;margin: 1rem 0;text-align: center;color: #166534;}
    .admin-panel {background: #fef3c7;border: 2px solid #fbbf24;padding: 1.5rem;border-radius: 12px;margin: 2rem 0;}
    .db-status {background: #dbeafe;border: 1px solid #3b82f6;padding: 0.5rem 1rem;border-radius: 8px;margin: 0.5rem 0;font-size: 0.9rem;color: #1e40af;}
    @media (max-width: 768px) {
        .main-title {font-size: 1.8rem;margin-top: 4rem;}
        .toolbar {flex-wrap: wrap;gap: 0.5rem;padding: 0.6rem;}
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# ⚙️ الإعدادات
# ═══════════════════════════════════════════════════════════════

try:
    BOT_TOKENS = [st.secrets["bot1"], st.secrets["bot2"], st.secrets["bot3"]]
    CHANNEL_ID = st.secrets["channelid"]
    ADMIN_PASSWORD = st.secrets["password"]
    
    # رابط Google Drive
    GDRIVE_FILE_ID = st.secrets.get("gdrive_file_id", "")
    
    # بيانات MTProto للتحميل الكامل (اختياري)
    USER_API_ID = st.secrets.get("user_api_id", "")
    USER_API_HASH = st.secrets.get("user_api_hash", "")
    USER_SESSION_STRING = st.secrets.get("user_session_string", "")
    
except:
    st.error("⚠️ خطأ في تحميل الإعدادات")
    st.stop()

# مسار مؤقت لقاعدة البيانات
DATABASE_FILE = "/tmp/books.db"
DB_CACHE_TIME = 300  # 5 دقائق

SESSION_TIMEOUT = 600
MIN_REQUEST_INTERVAL = 3  # ⚡ 3 ثواني بين كل تحميل
MAX_REQUESTS_PER_MINUTE = 15  # ⚡ الحد الأقصى لكل بوت
LARGE_FILE_MIN_INTERVAL = 8  # ⚡ 8 ثواني للملفات الكبيرة (+5MB)
LARGE_FILE_THRESHOLD_MB = 5  # الملفات أكبر من 5MB تعتبر كبيرة

# إعدادات جلسة المستخدم (MTProto)
USER_SESSION_MIN_INTERVAL = 10  # ⚡ 10 ثواني بين التحميلات عبر جلسة المستخدم
USER_SESSION_MAX_SIZE_MB = 2000  # الحد الأقصى 2GB

# ═══════════════════════════════════════════════════════════════
# متغيرات الجلسة
# ═══════════════════════════════════════════════════════════════

for key in ['active_sessions', 'current_bot_index', 'session_id', 'is_admin', 'bot_requests', 'show_counter', 'search_results', 'session_start_time', 'downloads_count', 'search_cache', 'search_history', 'db_loaded', 'db_last_update', 'db_size', 'last_download_time', 'last_large_download_time', 'downloading_now', 'last_user_session_download', 'user_session_downloads_count']:
    if key not in st.session_state:
        if key == 'bot_requests':
            st.session_state[key] = {i: [] for i in range(len(BOT_TOKENS))}
        elif key in ['active_sessions', 'search_cache', 'search_history']:
            st.session_state[key] = {}
        elif key in ['show_counter', 'is_admin', 'db_loaded', 'downloading_now']:
            st.session_state[key] = False
        elif key in ['downloads_count', 'current_bot_index', 'db_last_update', 'db_size', 'user_session_downloads_count']:
            st.session_state[key] = 0
        elif key in ['last_download_time', 'last_large_download_time', 'last_user_session_download']:
            st.session_state[key] = 0.0
        else:
            st.session_state[key] = None

# التحقق من توفر Session String
USER_SESSION_AVAILABLE = bool(USER_API_ID and USER_API_HASH and USER_SESSION_STRING)

# ═══════════════════════════════════════════════════════════════
# 📥 تحميل قاعدة البيانات من Google Drive
# ═══════════════════════════════════════════════════════════════

def extract_file_id(url_or_id):
    """استخراج File ID من رابط أو إرجاع ID مباشرة"""
    if not url_or_id:
        return None
    
    if len(url_or_id) < 50 and '/' not in url_or_id:
        return url_or_id
    
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/folders/([a-zA-Z0-9_-]+)',
        r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return url_or_id

def download_db_from_gdrive():
    """تحميل قاعدة البيانات من Google Drive"""
    
    if not GDRIVE_FILE_ID:
        st.error("⚠️ لم يتم تعيين gdrive_file_id في الإعدادات!")
        return False
    
    if os.path.exists(DATABASE_FILE):
        file_age = time.time() - os.path.getmtime(DATABASE_FILE)
        if file_age < DB_CACHE_TIME:
            return True
    
    try:
        file_id = extract_file_id(GDRIVE_FILE_ID)
        
        if not file_id:
            st.error("❌ File ID غير صحيح!")
            return False
        
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        with st.spinner("🔄 جاري تحميل قاعدة البيانات من Google Drive..."):
            response = requests.get(download_url, stream=True, timeout=30)
            
            if 'confirm' in response.text.lower():
                confirm_token = None
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        confirm_token = value
                        break
                
                if confirm_token:
                    download_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}"
                    response = requests.get(download_url, stream=True, timeout=30)
            
            if response.status_code == 200:
                total_size = 0
                with open(DATABASE_FILE, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            total_size += len(chunk)
                
                st.session_state.db_loaded = True
                st.session_state.db_last_update = time.time()
                st.session_state.db_size = total_size / (1024 * 1024)
                
                return True
            else:
                st.error(f"❌ فشل التحميل: HTTP {response.status_code}")
                return False
                
    except requests.exceptions.Timeout:
        st.error("❌ انتهت مهلة التحميل. حاول مرة أخرى.")
        return False
    except Exception as e:
        st.error(f"❌ خطأ في التحميل: {str(e)}")
        return False

def force_reload_db():
    """إعادة تحميل قاعدة البيانات بالقوة"""
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
    st.session_state.db_loaded = False
    return download_db_from_gdrive()

# ═══════════════════════════════════════════════════════════════
# 🔍 دوال قاعدة البيانات
# ═══════════════════════════════════════════════════════════════

def get_db_connection():
    """الاتصال بقاعدة البيانات"""
    
    if not st.session_state.db_loaded or not os.path.exists(DATABASE_FILE):
        if not download_db_from_gdrive():
            return None
    
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"❌ خطأ في الاتصال: {str(e)}")
        return None

def normalize_arabic_text(text):
    if not text:
        return ""
    text = re.sub(r'[\u064B-\u065F]', '', text)
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return ' '.join(text.split()).lower().strip()

def get_cache_key(query, filters):
    return hashlib.md5(f"{query}_{str(sorted(filters.items()))}".encode()).hexdigest()

def get_cached_search(cache_key):
    if cache_key in st.session_state.search_cache:
        cached_data, timestamp = st.session_state.search_cache[cache_key]
        if datetime.now().timestamp() - timestamp < 600:
            return cached_data
    return None

def cache_search(cache_key, results):
    if len(st.session_state.search_cache) > 50:
        oldest = min(st.session_state.search_cache.keys(), key=lambda k: st.session_state.search_cache[k][1])
        del st.session_state.search_cache[oldest]
    st.session_state.search_cache[cache_key] = (results, datetime.now().timestamp())

def build_search_sql(words, filters):
    sql_parts, params = [], []
    if words:
        conditions = []
        for word in words:
            conditions.append("(file_name LIKE ? OR description LIKE ?)")
            params.extend([f'%{word}%', f'%{word}%'])
        if conditions:
            sql_parts.append("(" + " AND ".join(conditions) + ")")
    if filters.get('format') and filters['format'] != 'all':
        sql_parts.append("file_extension = ?")
        params.append(filters['format'])
    if filters.get('min_size'):
        sql_parts.append("size_mb >= ?")
        params.append(filters['min_size'])
    if filters.get('max_size'):
        sql_parts.append("size_mb <= ?")
        params.append(filters['max_size'])
    return " AND ".join(sql_parts) if sql_parts else "1=1", params

def calculate_relevance_score(row, words):
    score = 0
    name = normalize_arabic_text(row['file_name'])
    desc = normalize_arabic_text(row['description'] or '')
    for word in words:
        score += name.count(word) * 10 + desc.count(word) * 3
        if name.startswith(word):
            score += 20
    return score

def search_books_advanced(query, filters=None, limit=50):
    if not query or len(query) < 2:
        return []
    filters = filters or {}
    cache_key = get_cache_key(query, filters)
    cached = get_cached_search(cache_key)
    if cached:
        return cached[:limit]
    words = [w for w in normalize_arabic_text(query).split() if len(w) > 1]
    if not words:
        return []
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        where, params = build_search_sql(words, filters)
        cursor.execute(f"SELECT * FROM books WHERE {where} LIMIT ?", params + [limit * 3])
        results = cursor.fetchall()
        conn.close()
        scored = [(calculate_relevance_score(dict(r), words), dict(r)) for r in results]
        scored.sort(key=lambda x: x[0], reverse=True)
        final = [r[1] for r in scored[:limit]]
        cache_search(cache_key, final)
        return final
    except Exception as e:
        st.error(f"❌ خطأ في البحث: {str(e)}")
        return []

def get_available_formats():
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT file_extension, COUNT(*) as count FROM books WHERE file_extension IS NOT NULL GROUP BY file_extension ORDER BY count DESC")
        results = cursor.fetchall()
        conn.close()
        return [(r['file_extension'], r['count']) for r in results]
    except:
        return []

def get_db_stats():
    """الحصول على إحصائيات قاعدة البيانات"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM books")
        total = cursor.fetchone()['total']
        conn.close()
        return {"total_books": total}
    except:
        return None

def get_autocomplete_suggestions(query, limit=5):
    if not query or len(query) < 2:
        return []
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT file_name FROM books WHERE file_name LIKE ? LIMIT ?", (f'%{query}%', limit * 2))
        results = cursor.fetchall()
        conn.close()
        suggestions = []
        for r in results:
            suggestion = ' '.join(r['file_name'].split()[:3])
            if suggestion not in suggestions:
                suggestions.append(suggestion)
        return suggestions[:limit]
    except:
        return []

def add_to_search_history(query):
    query = query.strip().lower()
    if len(query) >= 2:
        st.session_state.search_history[query] = st.session_state.search_history.get(query, 0) + 1

def get_popular_searches(limit=10):
    return [s[0] for s in sorted(st.session_state.search_history.items(), key=lambda x: x[1], reverse=True)[:limit]]

def calculate_session_limit():
    current_time = time.time()
    total = 0
    for idx, requests in st.session_state.bot_requests.items():
        recent = [r for r in requests if current_time - r < 60]
        st.session_state.bot_requests[idx] = recent
        total += len(recent)
    ratio = total / (MAX_REQUESTS_PER_MINUTE * len(BOT_TOKENS))
    return 5 if ratio < 0.3 else 3 if ratio < 0.6 else 2 if ratio < 0.8 else 1

def clean_old_sessions():
    current_time = time.time()
    expired = [sid for sid, data in st.session_state.active_sessions.items() if current_time - data['start_time'] > SESSION_TIMEOUT]
    for sid in expired:
        del st.session_state.active_sessions[sid]
    return len(expired)

def can_start_session():
    clean_old_sessions()
    max_s = calculate_session_limit()
    current_s = len(st.session_state.active_sessions)
    return current_s < max_s, max_s, current_s

def get_session_id():
    ua = st.context.headers.get("User-Agent", "")
    return hashlib.md5(f"{ua}{time.time()}".encode()).hexdigest()[:12]

def start_session():
    sid = get_session_id()
    st.session_state.active_sessions[sid] = {'start_time': time.time(), 'downloads': 0, 'searches': 0}
    st.session_state.session_id = sid
    st.session_state.session_start_time = time.time()
    st.session_state.downloads_count = 0
    return sid

def end_session():
    if st.session_state.session_id and st.session_state.session_id in st.session_state.active_sessions:
        del st.session_state.active_sessions[st.session_state.session_id]
        st.session_state.session_id = None
        st.session_state.session_start_time = None
        st.session_state.downloads_count = 0

def update_session_activity(activity='search'):
    if st.session_state.session_id in st.session_state.active_sessions:
        if activity == 'download':
            st.session_state.active_sessions[st.session_state.session_id]['downloads'] += 1
            st.session_state.downloads_count += 1
        else:
            st.session_state.active_sessions[st.session_state.session_id]['searches'] += 1

def get_best_bot():
    """اختيار أفضل بوت متاح مع توزيع الحمل"""
    current_time = time.time()
    best_idx, min_req = 0, float('inf')
    
    for idx in range(len(BOT_TOKENS)):
        recent = [r for r in st.session_state.bot_requests[idx] if current_time - r < 60]
        st.session_state.bot_requests[idx] = recent
        
        if len(recent) < min_req:
            min_req, best_idx = len(recent), idx
    
    st.session_state.bot_requests[best_idx].append(current_time)
    
    return BOT_TOKENS[best_idx], best_idx

def check_download_cooldown(file_size_mb=0):
    """
    التحقق من فترة الانتظار بين التحميلات
    - ملفات عادية: 3 ثواني
    - ملفات كبيرة (+5MB): 8 ثواني
    """
    current_time = time.time()
    is_large_file = file_size_mb >= LARGE_FILE_THRESHOLD_MB
    
    if is_large_file:
        last_time = st.session_state.last_large_download_time
        required_interval = LARGE_FILE_MIN_INTERVAL
        file_type = "كبير"
    else:
        last_time = st.session_state.last_download_time
        required_interval = MIN_REQUEST_INTERVAL
        file_type = "عادي"
    
    if last_time > 0:
        elapsed = current_time - last_time
        remaining = required_interval - elapsed
        
        if remaining > 0:
            return False, remaining, file_type
    
    return True, 0, file_type

def check_user_session_cooldown():
    """التحقق من فترة الانتظار لجلسة المستخدم"""
    if not USER_SESSION_AVAILABLE:
        return False, 0
    
    current_time = time.time()
    last_time = st.session_state.last_user_session_download
    
    if last_time > 0:
        elapsed = current_time - last_time
        remaining = USER_SESSION_MIN_INTERVAL - elapsed
        
        if remaining > 0:
            return False, remaining
    
    return True, 0

def update_download_time(file_size_mb=0):
    """تحديث وقت آخر تحميل"""
    current_time = time.time()
    is_large_file = file_size_mb >= LARGE_FILE_THRESHOLD_MB
    
    if is_large_file:
        st.session_state.last_large_download_time = current_time
    
    st.session_state.last_download_time = current_time

def update_user_session_time():
    """تحديث وقت آخر تحميل لجلسة المستخدم"""
    st.session_state.last_user_session_download = time.time()
    st.session_state.user_session_downloads_count += 1

def get_bot_health_status():
    """الحصول على حالة البوتات الصحية"""
    current_time = time.time()
    statuses = []
    
    for idx in range(len(BOT_TOKENS)):
        recent = [r for r in st.session_state.bot_requests[idx] if current_time - r < 60]
        usage_percent = (len(recent) / MAX_REQUESTS_PER_MINUTE) * 100
        
        if usage_percent < 50:
            status = "🟢 ممتاز"
        elif usage_percent < 75:
            status = "🟡 جيد"
        else:
            status = "🔴 مشغول"
        
        statuses.append({
            'bot_num': idx + 1,
            'requests': len(recent),
            'usage_percent': usage_percent,
            'status': status
        })
    
    return statuses

def remove_links_from_description(desc):
    if not desc:
        return ""
    desc = re.sub(r'http[s]?://\S+', '', desc)
    desc = re.sub(r't\.me/\S+', '', desc)
    desc = re.sub(r'@\w+', '', desc)
    return desc.strip()

def download_from_telegram(file_id, file_name="", file_size_mb=0):
    """
    تحميل ملف من تيليجرام مع حماية كاملة من الحظر
    """
    
    # 🔒 منع التحميلات المتعددة المتزامنة
    if st.session_state.downloading_now:
        st.error("❌ يوجد تحميل جاري حالياً. انتظر حتى ينتهي.")
        return None
    
    # 🔒 التحقق من فترة الانتظار
    can_download, wait_time, file_type = check_download_cooldown(file_size_mb)
    
    if not can_download:
        st.warning(f"⏰ يرجى الانتظار {wait_time:.1f} ثانية قبل التحميل التالي (ملف {file_type})")
        
        placeholder = st.empty()
        for remaining in range(int(wait_time), 0, -1):
            placeholder.warning(f"⏳ انتظر {remaining} ثانية...")
            time.sleep(1)
        placeholder.empty()
    
    # 🔒 قفل التحميل
    st.session_state.downloading_now = True
    
    try:
        bot_token, bot_idx = get_best_bot()
        
        if st.session_state.show_counter or st.session_state.is_admin:
            st.info(f"🤖 استخدام البوت #{bot_idx + 1}")
        
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile"
        response = requests.get(get_file_url, params={'file_id': file_id}, timeout=15)
        
        # التعامل مع Rate Limit
        if response.status_code == 429:
            retry_after = response.json().get('parameters', {}).get('retry_after', 5)
            st.warning(f"⚠️ البوت #{bot_idx + 1} محظور مؤقتاً. الانتظار {retry_after} ثانية...")
            
            for _ in range(10):
                st.session_state.bot_requests[bot_idx].append(time.time())
            
            time.sleep(retry_after)
            
            st.session_state.downloading_now = False
            return download_from_telegram(file_id, file_name, file_size_mb)
        
        if response.status_code != 200:
            st.error(f"❌ خطأ في الحصول على معلومات الملف: {response.status_code}")
            return None
        
        data = response.json()
        
        if not data.get('ok'):
            error_desc = data.get('description', 'خطأ غير معروف')
            st.error(f"❌ {error_desc}")
            return None
        
        file_path = data['result'].get('file_path')
        file_size = data['result'].get('file_size', 0)
        
        if not file_path:
            st.error("❌ لم يتم العثور على مسار الملف")
            return None
        
        max_size = 20 * 1024 * 1024
        if file_size > max_size:
            st.error(f"❌ الملف كبير جداً ({file_size / (1024*1024):.1f} MB). الحد الأقصى 20 MB")
            st.info(f"💡 افتح القناة: https://t.me/{CHANNEL_ID.replace('@', '')}")
            return None
        
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        
        with st.spinner(f"📥 جاري التحميل من البوت #{bot_idx + 1}... ({file_size / (1024*1024):.1f} MB)"):
            file_response = requests.get(download_url, timeout=120, stream=True)
            
            if file_response.status_code == 200:
                update_session_activity('download')
                
                total_size = int(file_response.headers.get('content-length', 0))
                downloaded = 0
                chunks = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        chunks.append(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = downloaded / total_size
                            progress_bar.progress(progress)
                            status_text.text(f"تم تحميل: {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB")
                
                progress_bar.empty()
                status_text.empty()
                
                update_download_time(file_size_mb)
                
                return b''.join(chunks)
            else:
                st.error(f"❌ فشل التحميل: HTTP {file_response.status_code}")
                return None
                
    except requests.exceptions.Timeout:
        st.error("❌ انتهت مهلة التحميل. حاول مرة أخرى.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ خطأ في الاتصال بالإنترنت")
        return None
    except Exception as e:
        st.error(f"❌ خطأ غير متوقع: {str(e)}")
        return None
    finally:
        st.session_state.downloading_now = False

def download_large_file_via_user_session(file_id, file_name="", file_size_mb=0):
    """
    تحميل ملفات كبيرة (+20MB) عبر جلسة المستخدم MTProto
    يستخدم file_id من قاعدة البيانات مباشرة للتحميل - بدون بحث!
    """
    
    if not USER_SESSION_AVAILABLE:
        st.error("❌ جلسة المستخدم غير متوفرة. يرجى إضافة user_session_string في ملف الإعدادات.")
        return None
    
    if st.session_state.downloading_now:
        st.error("❌ يوجد تحميل جاري حالياً. انتظر حتى ينتهي.")
        return None
    
    can_download, wait_time = check_user_session_cooldown()
    
    if not can_download:
        st.warning(f"⏰ يرجى الانتظار {wait_time:.1f} ثانية قبل التحميل التالي")
        
        placeholder = st.empty()
        for remaining in range(int(wait_time), 0, -1):
            placeholder.warning(f"⏳ انتظر {remaining} ثانية...")
            time.sleep(1)
        placeholder.empty()
    
    st.session_state.downloading_now = True
    
    try:
        from telethon.sync import TelegramClient
        from telethon.sessions import StringSession
        import io
        
        client = TelegramClient(
            StringSession(USER_SESSION_STRING),
            USER_API_ID,
            USER_API_HASH
        )
        
        with client:
            with st.spinner(f"📥 جاري التحميل... ({file_size_mb:.1f} MB)"):
                
                file_buffer = io.BytesIO()
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def callback(current, total):
                    if total > 0:
                        progress = current / total
                        progress_bar.progress(min(progress, 1.0))
                        status_text.text(f"📊 {current / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB")
                
                client.download_file(
                    file_id,
                    file=file_buffer,
                    progress_callback=callback
                )
                
                progress_bar.empty()
                status_text.empty()
                
                file_buffer.seek(0)
                file_data = file_buffer.read()
                
                if not file_data:
                    st.error("❌ فشل تحميل البيانات")
                    return None
                
                update_session_activity('download')
                update_user_session_time()
                
                return file_data
                
    except ImportError:
        st.error("❌ مكتبة Telethon غير مثبتة.")
        st.code("pip install telethon", language="bash")
        return None
    except Exception as e:
        st.error(f"❌ خطأ في التحميل: {str(e)}")
        
        if st.session_state.is_admin:
            import traceback
            with st.expander("🔍 تفاصيل الخطأ"):
                st.code(traceback.format_exc())
        
        return None
    finally:
        st.session_state.downloading_now = False

def render_book_card(row):
    """عرض بطاقة الكتاب مع زر التحميل"""
    desc = remove_links_from_description(row.get('description', ''))
    colors = {'pdf': '#ef4444', 'epub': '#8b5cf6', 'mobi': '#3b82f6', 'doc': '#10b981', 'docx': '#10b981'}
    color = colors.get(row.get('file_extension', ''), '#6b7280')
    
    file_size_mb = row.get('size_mb', 0)
    is_large = file_size_mb >= LARGE_FILE_THRESHOLD_MB
    is_very_large = file_size_mb > 20
    
    st.markdown(f"""
    <div class="result-card">
        <div class="book-title">📖 {row.get('file_name', 'بدون عنوان')}</div>
        <div class="book-meta">
            <span style="background: {color}; color: white; padding: 0.2rem 0.6rem; border-radius: 5px; font-size: 0.8rem;">
                {row.get('file_extension', 'N/A').upper()}
            </span>
            <span>📄 {row.get('pages', 'غير محدد')} صفحة</span>
            <span>💾 {file_size_mb:.1f} MB</span>
            {f'<span style="background: #f59e0b; color: white; padding: 0.2rem 0.6rem; border-radius: 5px; font-size: 0.75rem;">⚡ ملف كبير</span>' if is_large else ''}
            {f'<span style="background: #ef4444; color: white; padding: 0.2rem 0.6rem; border-radius: 5px; font-size: 0.75rem;">🔥 ملف ضخم</span>' if is_very_large else ''}
        </div>
        {f'<div class="book-description">{desc[:300]}...</div>' if desc and len(desc) > 0 else ''}
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        file_id = row.get('file_id', '')
        file_name = row.get('file_name', 'book')
        file_ext = row.get('file_extension', 'pdf')
        
        if file_size_mb > USER_SESSION_MAX_SIZE_MB:
            st.error(f"❌ الملف ضخم جداً ({file_size_mb:.1f} MB). الحد الأقصى {USER_SESSION_MAX_SIZE_MB} MB")
            if st.button(f"🔗 فتح في القناة", key=f"ch_{row.get('id')}", use_container_width=True):
                channel_link = f"https://t.me/{CHANNEL_ID.replace('@', '')}"
                st.info(f"افتح القناة: {channel_link}")
        
        elif is_very_large:
            if USER_SESSION_AVAILABLE:
                can_download, wait_time = check_user_session_cooldown()
                
                button_label = f"⬇️ تحميل ({file_size_mb:.1f} MB) 🔥"
                
                if not can_download:
                    st.warning(f"⏰ انتظر {wait_time:.0f}ث قبل التحميل")
                
                button_disabled = st.session_state.downloading_now or not can_download
                
                if st.button(
                    button_label,
                    key=f"dl_user_{row.get('id')}",
                    use_container_width=True,
                    type="secondary",
                    disabled=button_disabled
                ):
                    if not file_id:
                        st.error("❌ معرف الملف غير موجود")
                    else:
                        file_data = download_large_file_via_user_session(file_id, file_name, file_size_mb)
                        
                        if file_data:
                            if not file_name.endswith(f'.{file_ext}'):
                                file_name = f"{file_name}.{file_ext}"
                            
                            mime_types = {
                                'pdf': 'application/pdf',
                                'epub': 'application/epub+zip',
                                'mobi': 'application/x-mobipocket-ebook',
                                'doc': 'application/msword',
                                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                'txt': 'text/plain'
                            }
                            mime_type = mime_types.get(file_ext.lower(), 'application/octet-stream')
                            
                            st.download_button(
                                label="💾 حفظ الملف",
                                data=file_data,
                                file_name=file_name,
                                mime=mime_type,
                                key=f"sv_user_{row.get('id')}",
                                use_container_width=True
                            )
                            st.success("✅ الملف جاهز للتحميل!")
                            st.info(f"⏰ يمكنك تحميل ملف آخر بعد {USER_SESSION_MIN_INTERVAL} ثواني")
            else:
                st.warning(f"⚠️ الملف كبير ({file_size_mb:.1f} MB) - يحتاج جلسة مستخدم")
                
                if USER_API_ID and USER_API_HASH:
                    st.info("💡 المشرف: أضف user_session_string في Secrets")
                else:
                    st.info("💡 المشرف لم يفعّل التحميل الكامل بعد")
                
                if st.button(f"🔗 فتح في القناة", key=f"ch2_{row.get('id')}", use_container_width=True):
                    channel_link = f"https://t.me/{CHANNEL_ID.replace('@', '')}"
                    st.info(f"افتح القناة: {channel_link}")
        
        else:
            can_download, wait_time, file_type = check_download_cooldown(file_size_mb)
            
            button_label = f"⬇️ تحميل الكتاب ({file_size_mb:.1f} MB)"
            if is_large:
                button_label += " ⚡"
            
            if not can_download:
                st.warning(f"⏰ انتظر {wait_time:.0f}ث قبل التحميل التالي")
            
            button_disabled = st.session_state.downloading_now or not can_download
            
            if st.button(
                button_label, 
                key=f"dl_{row.get('id')}", 
                use_container_width=True, 
                type="primary",
                disabled=button_disabled
            ):
                if not file_id:
                    st.error("❌ معرف الملف غير موجود")
                else:
                    file_data = download_from_telegram(file_id, file_name, file_size_mb)
                    
                    if file_data:
                        if not file_name.endswith(f'.{file_ext}'):
                            file_name = f"{file_name}.{file_ext}"
                        
                        mime_types = {
                            'pdf': 'application/pdf',
                            'epub': 'application/epub+zip',
                            'mobi': 'application/x-mobipocket-ebook',
                            'doc': 'application/msword',
                            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                            'txt': 'text/plain'
                        }
                        mime_type = mime_types.get(file_ext.lower(), 'application/octet-stream')
                        
                        st.download_button(
                            label="💾 حفظ الملف",
                            data=file_data,
                            file_name=file_name,
                            mime=mime_type,
                            key=f"sv_{row.get('id')}",
                            use_container_width=True
                        )
                        st.success("✅ الملف جاهز للتحميل!")
                        
                        if is_large:
                            st.info(f"⏰ يمكنك تحميل ملف كبير آخر بعد {LARGE_FILE_MIN_INTERVAL} ثواني")
                        else:
                            st.info(f"⏰ يمكنك تحميل ملف آخر بعد {MIN_REQUEST_INTERVAL} ثواني")
    
    with col2:
        if st.button("ℹ️ تفاصيل", key=f"info_{row.get('id')}", use_container_width=True):
            with st.expander("📋 معلومات الكتاب", expanded=True):
                st.write(f"**الاسم:** {row.get('file_name', 'N/A')}")
                st.write(f"**الصيغة:** {row.get('file_extension', 'N/A').upper()}")
                st.write(f"**الحجم:** {file_size_mb:.2f} MB")
                st.write(f"**الصفحات:** {row.get('pages', 'غير محدد')}")
                
                if file_size_mb > USER_SESSION_MAX_SIZE_MB:
                    st.write(f"**النوع:** 💀 ضخم جداً (غير مدعوم)")
                elif is_very_large:
                    if USER_SESSION_AVAILABLE:
                        st.write(f"**النوع:** 🔥 ملف ضخم (جلسة المستخدم)")
                        st.write(f"**الانتظار:** {USER_SESSION_MIN_INTERVAL} ثانية")
                    else:
                        st.write(f"**النوع:** 🔥 ملف ضخم (غير متاح)")
                elif is_large:
                    st.write(f"**النوع:** ⚡ كبير (البوتات)")
                    st.write(f"**الانتظار:** {LARGE_FILE_MIN_INTERVAL} ثانية")
                else:
                    st.write(f"**النوع:** 📄 عادي (البوتات)")
                    st.write(f"**الانتظار:** {MIN_REQUEST_INTERVAL} ثانية")
                
                if desc:
                    st.write(f"**الوصف:**")
                    st.write(desc)

# ═══════════════════════════════════════════════════════════════
# واجهة المستخدم
# ═══════════════════════════════════════════════════════════════

if not st.session_state.db_loaded:
    download_db_from_gdrive()

clean_old_sessions()
can_start, max_sessions, current_sessions = can_start_session()
current_time = time.time()

toolbar_html = f"""
<div class="toolbar">
    <div style="display: flex; gap: 0.5rem; align-items: center;">
        <span style="font-weight: 600; font-size: 1.1rem;">📚 المكتبة الرقمية</span>
    </div>
    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
"""
if st.session_state.show_counter:
    usage_percent = (current_sessions / max_sessions * 100) if max_sessions > 0 else 0
    color = "#10b981" if usage_percent < 50 else "#f59e0b" if usage_percent < 80 else "#ef4444"
    toolbar_html += f'<span class="counter-badge" style="background: {color};">🔴 {current_sessions}/{max_sessions}</span>'
if st.session_state.is_admin:
    toolbar_html += '<span class="counter-badge" style="background: #f59e0b;">👑 مشرف</span>'
toolbar_html += "</div></div>"
st.markdown(toolbar_html, unsafe_allow_html=True)

if st.session_state.db_loaded:
    db_stats = get_db_stats()
    if db_stats:
        last_update = datetime.fromtimestamp(st.session_state.db_last_update)
        st.markdown(f"""
        <div class="db-status">
            📊 قاعدة البيانات: {db_stats['total_books']:,} كتاب | 
            💾 الحجم: {st.session_state.db_size:.1f} MB | 
            🔄 آخر تحديث: {last_update.strftime('%Y-%m-%d %H:%M')}
        </div>
        """, unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("▶️ بدء", use_container_width=True):
        if can_start or st.session_state.is_admin:
            start_session()
            st.success("✅ تم بدء الجلسة!")
            st.rerun()
        else:
            st.error(f"⚠️ الجلسات ممتلئة ({current_sessions}/{max_sessions})")
with col2:
    if st.button("⏹️ إنهاء", use_container_width=True):
        if st.session_state.session_id:
            end_session()
            st.success("✅ تم إنهاء الجلسة")
            st.rerun()
with col3:
    if st.button("🔢 عداد", use_container_width=True):
        st.session_state.show_counter = not st.session_state.show_counter
        st.rerun()
with col4:
    if not st.session_state.is_admin:
        if st.button("👤 مشرف", use_container_width=True):
            pass
    else:
        if st.button("🚪 خروج", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()

if not st.session_state.is_admin:
    with st.expander("🔐 دخول المشرف"):
        admin_pass = st.text_input("كلمة السر:", type="password", key="admin_login")
        if st.button("دخول", key="admin_login_btn"):
            if admin_pass == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.success("مرحباً أيها المشرف! 👑")
                st.rerun()
            else:
                st.error("كلمة سر خاطئة!")

if st.session_state.is_admin:
    with st.expander("🎛️ لوحة التحكم", expanded=True):
        st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
        
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            st.metric("الجلسات النشطة", current_sessions)
        with col_a2:
            st.metric("الحد الأقصى", max_sessions)
        with col_a3:
            usage = (current_sessions / max_sessions * 100) if max_sessions > 0 else 0
            st.metric("الاستخدام", f"{usage:.0f}%")
        
        if current_sessions > 0:
            st.warning(f"⚠️ يوجد {current_sessions} جلسة نشطة")
            if st.button("🚫 إنهاء جميع الجلسات", type="primary"):
                st.session_state.active_sessions = {}
                st.success("✅ تم إنهاء جميع الجلسات")
                st.rerun()
        
        st.markdown("### 🤖 إحصائيات البوتات")
        
        bot_statuses = get_bot_health_status()
        for status in bot_statuses:
            col_b1, col_b2, col_b3 = st.columns([2, 2, 1])
            with col_b1:
                st.text(f"البوت #{status['bot_num']}")
            with col_b2:
                st.text(f"{status['requests']}/{MAX_REQUESTS_PER_MINUTE} طلب/دقيقة ({status['usage_percent']:.0f}%)")
            with col_b3:
                st.text(status['status'])
        
        st.markdown("### 🛡️ نظام الحماية من الحظر")
        
        protection_info = f"""
        **📌 البوتات (للملفات < 20MB):**
        - ⏱️ التأخير بين التحميلات العادية: {MIN_REQUEST_INTERVAL} ثواني
        - ⚡ التأخير بين الملفات الكبيرة (+{LARGE_FILE_THRESHOLD_MB}MB): {LARGE_FILE_MIN_INTERVAL} ثواني
        - 🎯 حد الطلبات لكل بوت: {MAX_REQUESTS_PER_MINUTE} طلب/دقيقة
        - 🤖 عدد البوتات النشطة: {len(BOT_TOKENS)}
        
        **🔥 جلسة المستخدم (للملفات 20MB - 2GB):**
        - 📊 الحالة: {'✅ نشطة' if USER_SESSION_AVAILABLE else '❌ غير مفعّلة'}
        - ⏱️ التأخير بين التحميلات: {USER_SESSION_MIN_INTERVAL} ثواني
        - 📦 الحد الأقصى: {USER_SESSION_MAX_SIZE_MB} MB
        - 📥 عدد التحميلات: {st.session_state.user_session_downloads_count}
        
        **🔒 حماية عامة:**
        - منع التحميلات المتزامنة: {'✅ نشط' if not st.session_state.downloading_now else '🔴 جاري التحميل'}
        """
        
        st.info(protection_info)
        
        if st.session_state.last_download_time > 0:
            last_normal = time.time() - st.session_state.last_download_time
            st.text(f"⏰ آخر تحميل عادي (بوت): منذ {last_normal:.0f} ثانية")
        
        if st.session_state.last_large_download_time > 0:
            last_large = time.time() - st.session_state.last_large_download_time
            st.text(f"⚡ آخر تحميل كبير (بوت): منذ {last_large:.0f} ثانية")
        
        if st.session_state.last_user_session_download > 0:
            last_user = time.time() - st.session_state.last_user_session_download
            st.text(f"🔥 آخر تحميل (جلسة المستخدم): منذ {last_user:.0f} ثانية")
        
        st.markdown("### 🔥 إدارة جلسة المستخدم")
        
        if not (USER_API_ID and USER_API_HASH):
            st.warning("⚠️ لتفعيل التحميل الكامل، أضف في Streamlit Cloud Secrets:")
            st.code("""
user_api_id = "12345678"
user_api_hash = "your_api_hash_here"
user_session_string = "your_session_string_here"
            """, language="toml")
            
            with st.expander("📖 كيفية الحصول على البيانات"):
                st.markdown("""
                **1. احصل على API Credentials:**
                - اذهب إلى: https://my.telegram.org
                - سجل دخول برقم هاتفك
                - اختر "API Development Tools"
                - سجل تطبيق جديد
                - انسخ `api_id` و `api_hash`
                
                **2. احصل على Session String:**
                - على جهازك، ثبت: `pip install telethon`
                - شغل السكريبت التالي:
                
                ```python
                from telethon.sync import TelegramClient
                from telethon.sessions import StringSession
                
                API_ID = "12345678"
                API_HASH = "your_hash"
                
                with TelegramClient(StringSession(), API_ID, API_HASH) as client:
                    print("Session String:")
                    print(client.session.save())
                ```
                
                - سيطلب منك رقم الهاتف وكود التحقق
                - انسخ Session String الذي سيظهر
                - أضفه في Streamlit Cloud Secrets
                """)
        
        elif not USER_SESSION_AVAILABLE:
            st.warning("⚠️ Session String غير موجود")
            st.info("💡 أضف user_session_string في Streamlit Cloud Secrets")
        
        else:
            st.success(f"✅ جلسة المستخدم نشطة!")
            
            if st.button("📋 عرض Session String", use_container_width=True):
                st.code(USER_SESSION_STRING, language="text")
                st.warning("⚠️ لا تشارك هذا النص مع أحد!")
        
        st.markdown("### 📊 إدارة قاعدة البيانات")
        col_db1, col_db2 = st.columns(2)
        
        with col_db1:
            if st.button("🔄 إعادة تحميل القاعدة", use_container_width=True):
                with st.spinner("جاري التحميل..."):
                    if force_reload_db():
                        st.success("✅ تم إعادة التحميل!")
                        st.rerun()
                    else:
                        st.error("❌ فشل التحميل")
        
        with col_db2:
            if st.session_state.db_loaded:
                st.info(f"✅ القاعدة محمّلة ({st.session_state.db_size:.1f} MB)")
            else:
                st.warning("⚠️ القاعدة غير محمّلة")
        
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state.session_id and not st.session_state.is_admin:
    if not can_start:
        wait_time = SESSION_TIMEOUT // 60
        st.markdown(f"""
        <div class="wait-message">
            <h2 style="color: #667eea; margin-bottom: 1rem;">⏳ يرجى الانتظار</h2>
            <p style="font-size: 1.1rem; color: #4b5563;">جميع الجلسات مشغولة حالياً</p>
            <p style="color: #6b7280; margin-top: 1rem;">الحد الحالي: {max_sessions} جلسة متزامنة</p>
            <p style="color: #6b7280;">يتم التحديث كل {wait_time} دقيقة</p>
            <div style="margin-top: 2rem;">
                <span class="counter-badge" style="font-size: 1rem;">{current_sessions}/{max_sessions}</span>
            </div>
            <p style="font-size: 0.9rem; color: #9ca3af; margin-top: 1.5rem;">💡 الحد الأقصى يتغير تلقائياً حسب الاستخدام</p>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(3)
        st.rerun()
    else:
        st.markdown('<h1 class="main-title">ابحث في مكتبتك الرقمية</h1>', unsafe_allow_html=True)
        st.info("🔔 يرجى بدء جلسة أولاً للبحث والتحميل")
else:
    if st.session_state.session_id:
        elapsed = int(current_time - st.session_state.session_start_time)
        remaining = SESSION_TIMEOUT - elapsed
        progress = elapsed / SESSION_TIMEOUT
        st.markdown(f"""
        <div class="session-info">
            ✅ جلسة نشطة • التحميلات: {st.session_state.downloads_count} • الوقت المتبقي: {remaining // 60} دقيقة
        </div>
        """, unsafe_allow_html=True)
        st.progress(progress)
    
    st.markdown('<h1 class="main-title">🔍 ابحث في مكتبتك الرقمية</h1>', unsafe_allow_html=True)
    
    with st.expander("⚙️ فلاتر متقدمة", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            formats = get_available_formats()
            format_options = [('all', 'جميع الصيغ')] + [(f[0], f"{f[0].upper()} ({f[1]})") for f in formats[:10]]
            selected_format = st.selectbox(
                "الصيغة",
                options=[f[0] for f in format_options],
                format_func=lambda x: dict(format_options)[x],
                key="format_filter"
            )
        with col2:
            min_size = st.number_input("الحجم الأدنى (MB)", min_value=0.0, value=0.0, step=1.0, key="min_size")
        with col3:
            max_size = st.number_input("الحجم الأقصى (MB)", min_value=0.0, value=0.0, step=1.0, key="max_size")
        with col4:
            limit = st.selectbox("عدد النتائج", [20, 50, 100], index=0, key="limit")
    
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_query = st.text_input(
            "",
            placeholder="🔍 ابحث عن كتاب... (مثال: فيزياء كلاسيكية)",
            key="search_input",
            label_visibility="collapsed"
        )
    with col_btn:
        search_clicked = st.button("بحث", type="primary", use_container_width=True, key="search_btn")
    
    if search_query and len(search_query) >= 2 and not search_clicked:
        suggestions = get_autocomplete_suggestions(search_query)
        if suggestions:
            st.info(f"💡 اقتراحات: {' • '.join(suggestions[:3])}")
    
    popular = get_popular_searches(5)
    if popular and not search_query:
        st.markdown("**🔥 الأكثر بحثاً:** " + " • ".join([f"`{s}`" for s in popular]))
    
    if (search_query and len(search_query) >= 2) or search_clicked:
        filters = {
            'format': selected_format if selected_format != 'all' else None,
            'min_size': min_size if min_size > 0 else None,
            'max_size': max_size if max_size > 0 else None
        }
        add_to_search_history(search_query)
        
        with st.spinner("🔍 جاري البحث..."):
            results = search_books_advanced(search_query, filters, limit)
            st.session_state.search_results = results
            update_session_activity('search')
        
        if results:
            st.success(f"✨ تم العثور على {len(results)} نتيجة")
            
            sort_option = st.radio(
                "ترتيب حسب:",
                ["الصلة", "الاسم", "الحجم", "الصفحات"],
                horizontal=True,
                key="sort_option"
            )
            
            if sort_option == "الاسم":
                results = sorted(results, key=lambda x: x.get('file_name', ''))
            elif sort_option == "الحجم":
                results = sorted(results, key=lambda x: x.get('size_mb', 0), reverse=True)
            elif sort_option == "الصفحات":
                results = sorted(results, key=lambda x: x.get('pages') or 0, reverse=True)
            
            for row in results:
                render_book_card(row)
        else:
            st.warning("😔 لم يتم العثور على نتائج. جرّب كلمات مختلفة أو استخدم الفلاتر.")
            if search_query:
                st.info("💡 جرّب: كلمات أقصر، إزالة التشكيل، أو استخدام صيغة مختلفة")