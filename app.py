import streamlit as st
import sqlite3
import requests
import time
import os
from datetime import datetime, timedelta
import tempfile
from pathlib import Path
import hashlib

# ═══════════════════════════════════════════════════════════
# إعدادات الصفحة
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="المكتبة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════
# CSS مخصص للتصميم الراقي والبسيط
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background-color: #ffffff;
    }
    
    .toolbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.8rem 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        z-index: 1000;
        direction: rtl;
    }
    
    .toolbar-button {
        background: rgba(255,255,255,0.2);
        border: 1px solid rgba(255,255,255,0.3);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.3s;
        backdrop-filter: blur(10px);
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    
    .toolbar-button:hover {
        background: rgba(255,255,255,0.3);
        transform: translateY(-2px);
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #667eea;
        margin-top: 5rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .result-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: all 0.3s;
        direction: rtl;
    }
    
    .result-card:hover {
        box-shadow: 0 4px 12px rgba(102,126,234,0.15);
        border-color: #667eea;
    }
    
    .book-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    
    .book-meta {
        color: #6b7280;
        font-size: 0.9rem;
        margin: 0.5rem 0;
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }
    
    .book-description {
        color: #4b5563;
        font-size: 0.95rem;
        line-height: 1.6;
        margin: 1rem 0;
        padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
    }
    
    .wait-message {
        max-width: 500px;
        margin: 6rem auto;
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-radius: 16px;
        border: 2px solid #667eea30;
    }
    
    .counter-badge {
        background: #667eea;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .session-info {
        background: #f0fdf4;
        border: 1px solid #86efac;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        text-align: center;
        color: #166534;
    }
    
    .admin-panel {
        background: #fef3c7;
        border: 2px solid #fbbf24;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 2rem 0;
    }
    
    @media (max-width: 768px) {
        .main-title {
            font-size: 1.8rem;
            margin-top: 4rem;
        }
        .toolbar {
            flex-wrap: wrap;
            gap: 0.5rem;
            padding: 0.6rem;
        }
        .book-meta {
            flex-direction: column;
            gap: 0.3rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# تحميل الإعدادات من Secrets
# ═══════════════════════════════════════════════════════════
try:
    BOT_TOKENS = [
        st.secrets["bot1"],
        st.secrets["bot2"],
        st.secrets["bot3"]
    ]
    CHANNEL_ID = st.secrets["channelid"]
    ADMIN_PASSWORD = st.secrets["password"]
except Exception as e:
    st.error("⚠️ خطأ في تحميل الإعدادات من Secrets. تأكد من إضافتها في لوحة التحكم.")
    st.stop()

# إعدادات الجلسات الذكية
DATABASE_FILE = "books.db"
SESSION_TIMEOUT = 600  # 10 دقائق
MIN_REQUEST_INTERVAL = 2  # ثانيتين بين الطلبات للبوت الواحد
MAX_REQUESTS_PER_MINUTE = 20  # حد أقصى للطلبات في الدقيقة
SMART_SESSION_THRESHOLD = 0.7  # 70% استخدام قبل التحذير

# ═══════════════════════════════════════════════════════════
# تهيئة Session State
# ═══════════════════════════════════════════════════════════
if 'active_sessions' not in st.session_state:
    st.session_state.active_sessions = {}
if 'current_bot_index' not in st.session_state:
    st.session_state.current_bot_index = 0
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'bot_requests' not in st.session_state:
    st.session_state.bot_requests = {i: [] for i in range(len(BOT_TOKENS))}
if 'show_counter' not in st.session_state:
    st.session_state.show_counter = False
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'session_start_time' not in st.session_state:
    st.session_state.session_start_time = None
if 'downloads_count' not in st.session_state:
    st.session_state.downloads_count = 0

# ═══════════════════════════════════════════════════════════
# دوال قاعدة البيانات
# ═══════════════════════════════════════════════════════════

def get_db_connection():
    """الاتصال بقاعدة البيانات"""
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"خطأ في الاتصال بقاعدة البيانات: {str(e)}")
        return None

def search_books(query, limit=20):
    """البحث في قاعدة البيانات"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        search_term = f"%{query}%"
        
        cursor.execute("""
            SELECT * FROM books 
            WHERE file_name LIKE ? OR description LIKE ?
            ORDER BY file_name
            LIMIT ?
        """, (search_term, search_term, limit))
        
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        st.error(f"خطأ في البحث: {str(e)}")
        return []

# ═══════════════════════════════════════════════════════════
# إدارة الجلسات الذكية
# ═══════════════════════════════════════════════════════════

def calculate_session_limit():
    """حساب الحد الأقصى للجلسات بناءً على الاستخدام الحالي"""
    current_time = time.time()
    
    # حساب عدد الطلبات في الدقيقة الأخيرة لكل البوتات
    total_requests = 0
    for bot_idx, requests in st.session_state.bot_requests.items():
        recent_requests = [r for r in requests if current_time - r < 60]
        st.session_state.bot_requests[bot_idx] = recent_requests
        total_requests += len(recent_requests)
    
    # حساب الحد الأقصى الديناميكي
    usage_ratio = total_requests / (MAX_REQUESTS_PER_MINUTE * len(BOT_TOKENS))
    
    if usage_ratio < 0.3:  # استخدام منخفض
        return 5
    elif usage_ratio < 0.6:  # استخدام متوسط
        return 3
    elif usage_ratio < 0.8:  # استخدام عالي
        return 2
    else:  # استخدام مرتفع جداً
        return 1

def clean_old_sessions():
    """تنظيف الجلسات القديمة"""
    current_time = time.time()
    expired_sessions = []
    
    for session_id, session_data in st.session_state.active_sessions.items():
        if current_time - session_data['start_time'] > SESSION_TIMEOUT:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del st.session_state.active_sessions[session_id]
        
    return len(expired_sessions)

def can_start_session():
    """التحقق من إمكانية بدء جلسة جديدة"""
    clean_old_sessions()
    max_sessions = calculate_session_limit()
    current_sessions = len(st.session_state.active_sessions)
    
    return current_sessions < max_sessions, max_sessions, current_sessions

def get_session_id():
    """إنشاء معرف جلسة فريد"""
    user_agent = st.context.headers.get("User-Agent", "")
    timestamp = str(time.time())
    raw = f"{user_agent}{timestamp}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def start_session():
    """بدء جلسة جديدة"""
    session_id = get_session_id()
    st.session_state.active_sessions[session_id] = {
        'start_time': time.time(),
        'downloads': 0,
        'searches': 0
    }
    st.session_state.session_id = session_id
    st.session_state.session_start_time = time.time()
    st.session_state.downloads_count = 0
    return session_id

def end_session():
    """إنهاء الجلسة الحالية"""
    if st.session_state.session_id and st.session_state.session_id in st.session_state.active_sessions:
        del st.session_state.active_sessions[st.session_state.session_id]
        st.session_state.session_id = None
        st.session_state.session_start_time = None
        st.session_state.downloads_count = 0
        cleanup_temp_files()

def update_session_activity(activity_type='search'):
    """تحديث نشاط الجلسة"""
    if st.session_state.session_id in st.session_state.active_sessions:
        if activity_type == 'download':
            st.session_state.active_sessions[st.session_state.session_id]['downloads'] += 1
            st.session_state.downloads_count += 1
        elif activity_type == 'search':
            st.session_state.active_sessions[st.session_state.session_id]['searches'] += 1

# ═══════════════════════════════════════════════════════════
# إدارة البوتات الذكية
# ═══════════════════════════════════════════════════════════

def get_best_bot():
    """اختيار أفضل بوت متاح"""
    current_time = time.time()
    best_bot_idx = 0
    min_recent_requests = float('inf')
    
    for idx in range(len(BOT_TOKENS)):
        # حساب الطلبات الأخيرة
        recent_requests = [r for r in st.session_state.bot_requests[idx] if current_time - r < 60]
        st.session_state.bot_requests[idx] = recent_requests
        
        # اختيار البوت الأقل استخداماً
        if len(recent_requests) < min_recent_requests:
            min_recent_requests = len(recent_requests)
            best_bot_idx = idx
    
    # تسجيل الطلب
    st.session_state.bot_requests[best_bot_idx].append(current_time)
    return BOT_TOKENS[best_bot_idx], best_bot_idx

def cleanup_temp_files():
    """تنظيف الملفات المؤقتة"""
    temp_dir = tempfile.gettempdir()
    for file in Path(temp_dir).glob("telegram_book_*"):
        try:
            if time.time() - file.stat().st_mtime > 3600:  # ساعة واحدة
                file.unlink()
        except:
            pass

def remove_links_from_description(description):
    """إزالة الروابط من الوصف"""
    if not description:
        return ""
    
    import re
    description = re.sub(r'http[s]?://\S+', '', description)
    description = re.sub(r't\.me/\S+', '', description)
    description = re.sub(r'@\w+', '', description)
    
    return description.strip()

# ═══════════════════════════════════════════════════════════
# دوال التحميل من التليجرام
# ═══════════════════════════════════════════════════════════

def download_from_telegram(file_id):
    """تحميل الملف من التليجرام مع إدارة ذكية"""
    bot_token, bot_idx = get_best_bot()
    
    try:
        # الحصول على معلومات الملف
        url = f"https://api.telegram.org/bot{bot_token}/getFile"
        response = requests.get(url, params={'file_id': file_id}, timeout=15)
        
        if response.status_code == 429:  # Rate limit
            st.warning("⏳ يرجى الانتظار قليلاً...")
            time.sleep(MIN_REQUEST_INTERVAL)
            return download_from_telegram(file_id)  # إعادة المحاولة
        
        if response.status_code == 200:
            data = response.json()
            if not data.get('ok'):
                return None
                
            file_path = data['result']['file_path']
            
            # تحميل الملف
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            file_response = requests.get(download_url, timeout=60, stream=True)
            
            if file_response.status_code == 200:
                update_session_activity('download')
                return file_response.content
        
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ انتهت مهلة الاتصال، يرجى المحاولة مرة أخرى")
        return None
    except Exception as e:
        st.error(f"خطأ: {str(e)}")
        return None

# ═══════════════════════════════════════════════════════════
# واجهة المستخدم
# ═══════════════════════════════════════════════════════════

# تنظيف دوري
clean_old_sessions()
cleanup_temp_files()

# حساب معلومات الجلسات
can_start, max_sessions, current_sessions = can_start_session()
current_time = time.time()

# شريط الأدوات العلوي
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

toolbar_html += """
    </div>
</div>
"""
st.markdown(toolbar_html, unsafe_allow_html=True)

# أزرار التحكم
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

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

# تسجيل دخول المشرف
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

# لوحة تحكم المشرف
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
        
        # إحصائيات البوتات
        st.markdown("### 🤖 إحصائيات البوتات")
        for idx in range(len(BOT_TOKENS)):
            recent = [r for r in st.session_state.bot_requests[idx] if current_time - r < 60]
            st.text(f"البوت {idx + 1}: {len(recent)} طلب في الدقيقة الأخيرة")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# منطقة البحث
# ═══════════════════════════════════════════════════════════

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
                <span class="counter-badge" style="font-size: 1rem;">
                    {current_sessions}/{max_sessions}
                </span>
            </div>
            <p style="font-size: 0.9rem; color: #9ca3af; margin-top: 1.5rem;">
                💡 الحد الأقصى يتغير تلقائياً حسب الاستخدام
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        time.sleep(3)
        st.rerun()
    else:
        st.markdown('<h1 class="main-title">ابحث في مكتبتك الرقمية</h1>', unsafe_allow_html=True)
        st.info("🔔 يرجى بدء جلسة أولاً للبحث والتحميل")
else:
    # معلومات الجلسة
    if st.session_state.session_id:
        elapsed = int(current_time - st.session_state.session_start_time)
        remaining = SESSION_TIMEOUT - elapsed
        progress = elapsed / SESSION_TIMEOUT
        
        st.markdown(f"""
        <div class="session-info">
            ✅ جلسة نشطة • التحميلات: {st.session_state.downloads_count} • 
            الوقت المتبقي: {remaining // 60} دقيقة
        </div>
        """, unsafe_allow_html=True)
        
        st.progress(progress)
    
    st.markdown('<h1 class="main-title">ابحث في مكتبتك الرقمية</h1>', unsafe_allow_html=True)
    
    # صندوق البحث
    search_query = st.text_input(
        "",
        placeholder="🔍 ابحث عن كتاب بالاسم أو الوصف...",
        key="search_input",
        label_visibility="collapsed"
    )
    
    if search_query and len(search_query) >= 2:
        with st.spinner("🔍 جاري البحث..."):
            results = search_books(search_query)
            st.session_state.search_results = results
            update_session_activity('search')
    
    # عرض النتائج
    if st.session_state.search_results:
        st.markdown(f"<p style='text-align: center; color: #6b7280; margin: 1rem 0;'>✨ تم العثور على {len(st.session_state.search_results)} نتيجة</p>", unsafe_allow_html=True)
        
        for idx, row in enumerate(st.session_state.search_results):
            description = remove_links_from_description(row['description'])
            
            st.markdown(f"""
            <div class="result-card">
                <div class="book-title">📖 {row['file_name']}</div>
                <div class="book-meta">
                    <span>📄 {row['pages']} صفحة</span>
                    <span>💾 {row['size_mb']} MB</span>
                </div>
                {f'<div class="book-description">{description}</div>' if description else ''}
            </div>
            """, unsafe_allow_html=True)
            
            col_dl, col_br = st.columns(2)
            
            with col_dl:
                if st.button(f"⬇️ تحميل", key=f"dl_{idx}", use_container_width=True):
                    with st.spinner("⏳ جاري التحميل من التليجرام..."):
                        file_content = download_from_telegram(row['file_id'])
                        if file_content:
                            st.download_button(
                                label="📥 حفظ الملف",
                                data=file_content,
                                file_name=f"{row['file_name']}.pdf",
                                mime="application/pdf",
                                key=f"save_{idx}",
                                use_container_width=True
                            )
                            st.success("✅ جاهز للتحميل!")
                        else:
                            st.error("❌ فشل التحميل، حاول مرة أخرى")
            
            with col_br:
                view_url = f"https://docs.google.com/viewer?url=https://api.telegram.org/file/bot{BOT_TOKENS[0]}/{row['file_id']}"
                st.markdown(f'<a href="{view_url}" target="_blank" style="display: block; text-align: center; padding: 0.5rem; background: white; color: #667eea; border: 2px solid #667eea; border-radius: 8px; text-decoration: none; font-weight: 500;">👁️ تصفح</a>', unsafe_allow_html=True)
    
    elif st.session_state.search_results is not None and len(st.session_state.search_results) == 0:
        st.info("😔 لم يتم العثور على نتائج، جرب كلمات بحث أخرى")

# تنظيف دوري في نهاية كل تحميل
if st.session_state.session_id:
    cleanup_temp_files()