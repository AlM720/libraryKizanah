import streamlit as st
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import nest_asyncio
import io
import time
import uuid

# تفعيل تعدد المهام لبيئة Streamlit
nest_asyncio.apply()

# إعداد الصفحة
st.set_page_config(page_title="TeleBooks - المكتبة الخاصة", page_icon="📚", layout="centered")

# --- ⚙️ إعدادات النظام ---
TIMEOUT_SECONDS = 180  # مدة الجلسة (3 دقائق) - يطرد المستخدم بعدها إذا لم يتفاعل

# التأكد من وجود البيانات في الأسرار
required_secrets = ["api_id", "api_hash", "session_string", "channel_id", "admin_password"]
if not all(key in st.secrets for key in required_secrets):
    st.error("⚠️ خطأ: تأكد من إعداد ملف secrets.toml بكامل البيانات (بما في ذلك admin_password).")
    st.stop()

# --- 🧠 الذاكرة المشتركة (Global State) ---
# هذه الذاكرة مشتركة بين جميع المستخدمين لمعرفة حالة القفل
@st.cache_resource
class GlobalState:
    def __init__(self):
        self.locked = False          # هل الموقع مشغول؟
        self.current_user_token = None # من هو المستخدم الحالي؟
        self.last_activity = 0       # متى آخر مرة ضغط زر؟

state = GlobalState()

# --- 🆔 تعريف المستخدم الحالي ---
if 'user_token' not in st.session_state:
    st.session_state.user_token = str(uuid.uuid4())

if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# --- 🔐 منطق الحارس (Access Control) ---
def check_access():
    current_time = time.time()
    
    # 1. تنظيف المستخدمين الخاملين (Timeout Logic)
    # إذا كان الموقع مشغولاً ولكن مر وقت طويل دون نشاط، نلغي القفل
    if state.locked and (current_time - state.last_activity > TIMEOUT_SECONDS):
        state.locked = False
        state.current_user_token = None
    
    # 2. هل أنت الآدمن؟ (دخول فوري دائماً)
    if st.session_state.is_admin:
        return "ADMIN_ACCESS"

    # 3. هل أنت المستخدم الذي حجز الدور حالياً؟
    if state.locked and state.current_user_token == st.session_state.user_token:
        # تحديث وقت النشاط لأن المستخدم موجود
        state.last_activity = current_time 
        return "USER_ACCESS"
    
    # 4. هل الموقع فارغ؟
    if not state.locked:
        return "READY_TO_ENTER"
        
    # 5. الموقع مشغول بشخص آخر
    return False

# فحص الحالة الحالية
status = check_access()

# ==========================================
# 🛑 السيناريو 1: الموقع مشغول (شاشة الانتظار)
# ==========================================
if status == False:
    st.error("⛔ عذراً، المكتبة مشغولة حالياً بمستخدم آخر!")
    
    # حساب الوقت المتبقي
    time_passed = int(time.time() - state.last_activity)
    time_left = TIMEOUT_SECONDS - time_passed
    if time_left < 0: time_left = 0
    
    st.info("لحماية الحساب من الحظر، يُسمح بدخول شخص واحد فقط.")
    st.warning(f"⏳ سيصبح الموقع متاحاً تلقائياً خلال {time_left} ثانية إذا لم يجدد المستخدم نشاطه.")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("🔄 تحقق من الإتاحة الآن"):
            st.rerun()
            
    st.markdown("---")
    
    # 🔐 مدخل الآدمن السري
    with st.expander("👑 دخول المالك فقط (Admin Override)"):
        password_attempt = st.text_input("كلمة المرور:", type="password", key="admin_pass_locked")
        if st.button("دخول إجباري"):
            if password_attempt == st.secrets["admin_password"]:
                st.session_state.is_admin = True
                st.success("تم التحقق! جاري الدخول...")
                st.rerun()
            else:
                st.error("كلمة المرور خاطئة!")
    
    st.stop() # إيقاف الكود هنا للمستخدم العادي

# ==========================================
# 👋 السيناريو 2: الموقع متاح (شاشة الترحيب)
# ==========================================
elif status == "READY_TO_ENTER":
    st.title("📚 TeleBooks - المكتبة")
    st.success("✅ النظام متاح الآن.")
    st.write("اضغط في الأسفل لحجز دورك وبدء البحث.")
    
    if st.button("🚀 ابدأ الاستخدام", type="primary"):
        state.locked = True
        state.current_user_token = st.session_state.user_token
        state.last_activity = time.time()
        st.rerun()
    
    # خيار دخول الآدمن أيضاً
    with st.expander("تسجيل دخول المالك"):
        password_attempt = st.text_input("كلمة المرور:", type="password", key="admin_pass_open")
        if st.button("دخول"):
            if password_attempt == st.secrets["admin_password"]:
                st.session_state.is_admin = True
                st.rerun()
    st.stop()

# ==========================================
# ✅ السيناريو 3: داخل التطبيق (Main App)
# ==========================================

# --- تحذير خاص للآدمن ---
if status == "ADMIN_ACCESS" and state.locked and state.current_user_token != st.session_state.user_token:
    st.warning("⚠️ **تنبيه هام:** هناك مستخدم عادي يستخدم الموقع الآن! أنت تتجاوز الدور. استخدامكما للموقع في نفس اللحظة قد يزيد خطر الحظر.")

# --- الشريط الجانبي وزر الخروج ---
with st.sidebar:
    if st.session_state.is_admin:
        st.write("👑 **حساب المدير**")
    else:
        st.write("👤 **مستخدم عادي**")
        # عداد الوقت للمستخدم العادي
        time_left_session = TIMEOUT_SECONDS - int(time.time() - state.last_activity)
        st.caption(f"الإغلاق التلقائي خلال: {time_left_session} ثانية")
        
    if st.button("🚪 إنهاء الجلسة والخروج", type="primary"):
        if st.session_state.is_admin:
            st.session_state.is_admin = False
        else:
            state.locked = False
            state.current_user_token = None
        st.rerun()

# --- دوال الاتصال (Backend) ---
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
            # وضع حد 30 نتيجة لتسريع العملية
            async for message in client.iter_messages(entity, search=query, limit=30):
                if message.file:
                    file_name = message.file.name or message.text[:20] or 'كتاب'
                    # إصلاح الامتداد
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
                col_prog.text(f"📥 جاري سحب الملف: {file_name}...")
                
                def callback(current, total):
                    progress_bar.progress(current / total)
                
                await client.download_media(message, buffer, progress_callback=callback)
                buffer.seek(0)
            else:
                st.error("الملف غير موجود")
        except Exception as e:
            st.error(f"فشل التحميل: {e}")
            return None
        finally:
            await client.disconnect()
            
    loop.run_until_complete(_download())
    loop.close()
    col_prog.empty()
    progress_bar.empty()
    return buffer, file_name

# --- واجهة التطبيق الرئيسية ---
st.title("🔎 محرك البحث")

if 'search_results' not in st.session_state:
    st.session_state.search_results = []

col_search, col_btn = st.columns([4, 1])
with col_search:
    query = st.text_input("بحث", placeholder="اسم الكتاب...", label_visibility="collapsed")
with col_btn:
    if st.button("بحث", use_container_width=True):
        if query:
            # تجديد النشاط لمنع الطرد
            state.last_activity = time.time()
            with st.spinner("جاري البحث..."):
                st.session_state.search_results = search_books_async(query)

# عرض النتائج
if st.session_state.search_results:
    st.write(f"النتائج: {len(st.session_state.search_results)}")
    st.divider()
    
    for item in st.session_state.search_results:
        with st.container():
            c1, c2 = st.columns([1, 4])
            with c1:
                st.write("📦")
                st.caption(f"{item['size'] / (1024*1024):.1f} MB")
            with c2:
                st.subheader(item['file_name'])
                with st.expander("وصف الملف"):
                    st.text(item['caption'])
                
                # زر التحميل
                btn_key = f"btn_{item['id']}"
                if st.button("⬇️ تحضير التحميل", key=btn_key):
                    # تجديد النشاط عند الضغط
                    state.last_activity = time.time()
                    
                    buff, fname = download_book_to_memory(item['id'])
                    if buff:
                        st.download_button(
                            label="💾 حفظ الملف بجهازك",
                            data=buff,
                            file_name=fname,
                            mime="application/octet-stream",
                            key=f"save_{item['id']}"
                        )
            st.divider()
