import streamlit as st
from telethon import TelegramClient
import asyncio
import os

# إعداد الصفحة
st.set_page_config(page_title="TeleBooks - تحميل الكتب", page_icon="📚")

# الحصول على بيانات API من secrets
api_id = st.secrets["api_id"]
api_hash = st.secrets["api_hash"]

# دالة للبحث عن الكتب
def search_books(query):
    try:
        # إنشاء حلقة حدث جديدة
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # تشغيل البحث
        client = TelegramClient("bot_session", api_id, api_hash)
        
        async def do_search():
            await client.start()
            channels = ['@BooksThief', '@librebook', '@pdfdrive']
            results = []
            
            for channel in channels:
                try:
                    st.info(f"البحث في {channel}...")
                    messages = await client.get_messages(channel, limit=30, search=query)
                    
                    for message in messages:
                        if message.file and message.file.name:
                            results.append({
                                'channel': channel,
                                'message_id': message.id,
                                'text': message.text or 'بدون وصف',
                                'file_name': message.file.name,
                                'size': message.file.size
                            })
                except Exception as e:
                    st.warning(f"خطأ في {channel}: {str(e)}")
            
            await client.disconnect()
            return results
        
        # تنفيذ البحث مع timeout
        results = loop.run_until_complete(asyncio.wait_for(do_search(), timeout=30))
        loop.close()
        return results
        
    except asyncio.TimeoutError:
        st.error("انتهت مهلة البحث. حاول مرة أخرى.")
        return []
    except Exception as e:
        st.error(f"حدث خطأ: {str(e)}")
        return []

# واجهة المستخدم
st.title("📚 TeleBooks - محرك البحث عن الكتب")
st.markdown("ابحث عن الكتب في قنوات تيليجرام")

# مربع البحث
query = st.text_input("🔍 ابحث عن كتاب:", placeholder="أدخل اسم الكتاب أو المؤلف")

# تهيئة session state لتتبع النتائج والصفحة الحالية
if 'results' not in st.session_state:
    st.session_state.results = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

if st.button("بحث"):
    if query:
        with st.spinner("جاري البحث في القنوات..."):
            results = search_books(query)
            
            if results:
                st.session_state.results = results
                st.session_state.current_index = 0
                st.success(f"✅ تم العثور على {len(results)} نتيجة")
            else:
                st.session_state.results = []
                st.info("❌ لم يتم العثور على نتائج")
    else:
        st.warning("الرجاء إدخال كلمة بحث")

# عرض النتيجة الحالية
if st.session_state.results:
    result = st.session_state.results[st.session_state.current_index]
    
    st.markdown("---")
    st.subheader(f"📖 {result['file_name']}")
    st.write(f"**القناة:** {result['channel']}")
    st.write(f"**الوصف:** {result['text'][:300]}...")
    st.write(f"**الحجم:** {result['size'] / (1024*1024):.2f} MB")
    st.markdown(f"### [📥 فتح في تيليجرام](https://t.me/{result['channel'][1:]}/{result['message_id']})")
    
    # عرض رقم النتيجة
    st.info(f"النتيجة {st.session_state.current_index + 1} من {len(st.session_state.results)}")
    
    # أزرار التنقل
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.current_index > 0:
            if st.button("⬅️ السابق"):
                st.session_state.current_index -= 1
                st.rerun()
    
    with col2:
        if st.session_state.current_index < len(st.session_state.results) - 1:
            if st.button("➡️ التالي"):
                st.session_state.current_index += 1
                st.rerun()

# معلومات إضافية
st.sidebar.title("معلومات")
st.sidebar.info("""
هذا التطبيق يبحث في قنوات تيليجرام الشهيرة للكتب.
القنوات المدعومة:
- BooksThief
- librebook  
- pdfdrive
""")