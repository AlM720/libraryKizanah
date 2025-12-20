import streamlit as st
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import nest_asyncio
import io  # للتعامل مع الملفات في الذاكرة

# تفعيل خاصية تعدد المهام
nest_asyncio.apply()

st.set_page_config(page_title="TeleBooks - مكتبة السحاب", page_icon="📚", layout="centered")

# --- 🔐 إعدادات الجلسة ---
if "api_id" in st.secrets:
    api_id = int(st.secrets["api_id"])
    api_hash = st.secrets["api_hash"]
    session_string = st.secrets["session_string"]
    channel_id = int(st.secrets["channel_id"])
else:
    st.error("⚠️ الرجاء إعداد ملف secrets.toml")
    st.stop()

# --- 🛠️ دوال المساعدة (Backend) ---

async def get_client():
    """إنشاء اتصال وإعادته"""
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.start()
    return client

def search_books_async(query):
    """دالة البحث غير المتزامن"""
    results = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _search():
        client = await get_client()
        try:
            entity = await client.get_entity(channel_id)
            async for message in client.iter_messages(entity, search=query, limit=50): # وضع حد 50 لتسريع البحث
                if message.file:
                    file_name = message.file.name or message.text[:20] or 'كتاب بدون عنوان'
                    # التأكد من وجود اسم للملف لعدم حدوث أخطاء عند التحميل
                    if not file_name.endswith(('.pdf', '.epub', '.rar', '.zip')):
                        file_name += ".pdf" 
                        
                    results.append({
                        'id': message.id,
                        'file_name': file_name,
                        'size': message.file.size,
                        'date': message.date,
                        'caption': message.text or "لا يوجد وصف",
                        'channel_title': entity.title,
                        'username': entity.username,
                        'channel_id': entity.id
                    })
        except Exception as e:
            st.error(f"خطأ في البحث: {e}")
        finally:
            await client.disconnect()

    loop.run_until_complete(_search())
    loop.close()
    return results

def download_book_to_memory(message_id):
    """تحميل الكتاب من تيليجرام إلى ذاكرة الرام"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    buffer = io.BytesIO()
    file_name = "downloaded_book"
    
    # عناصر واجهة المستخدم للتحديث
    progress_text = st.empty()
    progress_bar = st.progress(0)

    async def _download():
        nonlocal file_name
        client = await get_client()
        try:
            entity = await client.get_entity(channel_id)
            message = await client.get_messages(entity, ids=message_id)
            
            if message and message.file:
                file_name = message.file.name or "book.pdf"
                progress_text.text(f"📥 جاري تنزيل: {file_name}...")
                
                # دالة تتبع التقدم
                def callback(current, total):
                    percent = current / total
                    progress_bar.progress(percent)
                
                # التحميل إلى الذاكرة (buffer)
                await client.download_media(message, buffer, progress_callback=callback)
                buffer.seek(0) # العودة لبداية الملف
            else:
                st.error("الرسالة لا تحتوي على ملف!")
                
        except Exception as e:
            st.error(f"خطأ أثناء التحميل: {e}")
            return None
        finally:
            await client.disconnect()
            
    loop.run_until_complete(_download())
    loop.close()
    
    progress_text.empty()
    progress_bar.empty()
    return buffer, file_name

# --- 🎨 واجهة المستخدم (Frontend) ---

st.title("📚 TeleBooks")
st.caption("محرك بحث وتحميل الكتب من تيليجرام")

# حالة الجلسة
if 'search_results' not in st.session_state:
    st.session_state.search_results = []

# مربع البحث
col_search, col_btn = st.columns([4, 1])
with col_search:
    query = st.text_input("بحث", placeholder="اسم الكتاب، المؤلف...", label_visibility="collapsed")
with col_btn:
    search_clicked = st.button("🔍 بحث", use_container_width=True)

if search_clicked and query:
    with st.spinner("جاري البحث في الأرشيف..."):
        results = search_books_async(query)
        st.session_state.search_results = results
        if not results:
            st.warning("لم يتم العثور على نتائج.")

# عرض النتائج
if st.session_state.search_results:
    st.write(f"✅ تم العثور على {len(st.session_state.search_results)} نتيجة")
    st.divider()

    for item in st.session_state.search_results:
        with st.container():
            c1, c2 = st.columns([1, 4])
            
            with c1:
                st.write("📂")
                # حساب الحجم بالميجابايت
                size_mb = item['size'] / (1024 * 1024)
                st.caption(f"{size_mb:.2f} MB")
            
            with c2:
                st.subheader(item['file_name'])
                with st.expander("📝 قراءة الوصف"):
                    st.write(item['caption'])
                    st.caption(f"تاريخ النشر: {item['date'].strftime('%Y-%m-%d')}")

                # مفتاح فريد لكل زر لتجنب التعارض
                btn_key = f"dl_btn_{item['id']}"
                
                # المنطق: زر "تجهيز التحميل" يقوم بجلب الملف، ثم يظهر زر "حفظ الملف"
                if st.button("⬇️ تحضير للتحميل", key=btn_key):
                    with st.spinner("جاري سحب الملف من سيرفرات تيليجرام..."):
                        file_buffer, fname = download_book_to_memory(item['id'])
                        
                        if file_buffer:
                            st.success("✅ الملف جاهز!")
                            st.download_button(
                                label=f"💾 اضغط لحفظ ({fname})",
                                data=file_buffer,
                                file_name=fname,
                                mime="application/octet-stream",
                                key=f"save_{item['id']}"
                            )

            st.divider()

# --- ℹ️ الشريط الجانبي ---
with st.sidebar:
    st.header("معلومات")
    st.info("""
    **كيف يعمل التحميل؟**
    1. عند الضغط على **تحضير للتحميل**، يقوم النظام بسحب الكتاب من تيليجرام إلى الموقع مؤقتاً.
    2. سيظهر لك شريط تقدم.
    3. عند الانتهاء، سيظهر زر **حفظ** لتحميله لجهازك.
    """)
    
    if st.button("🔄 إعادة تعيين الجلسة"):
        st.session_state.clear()
        st.rerun()
