import streamlit as st
from telethon import TelegramClient
import asyncio
import os

# إعداد الصفحة
st.set_page_config(page_title="TeleBooks - تحميل الكتب", page_icon="📚")

# الحصول على بيانات API من secrets
api_id = st.secrets["api_id"]
api_hash = st.secrets["api_hash"]

# دالة لإنشاء عميل Telegram
async def get_client():
    client = TelegramClient("bot_session", api_id, api_hash,
                           connection_retries=2, request_retries=2, timeout=10)
    await client.start()
    return client

# دالة للبحث عن الكتب
async def search_books(query):
    client = await get_client()
    try:
        # البحث في القنوات المشهورة للكتب
        channels = ['@BooksThief', '@librebook', '@pdfdrive']
        results = []
        
        for channel in channels:
            try:
                messages = await client.get_messages(channel, limit=50, search=query)
                for message in messages:
                    if message.file:
                        results.append({
                            'channel': channel,
                            'message_id': message.id,
                            'text': message.text or 'بدون وصف',
                            'file_name': message.file.name or 'ملف',
                            'size': message.file.size
                        })
            except Exception as e:
                st.warning(f"تعذر البحث في {channel}: {str(e)}")
        
        return results
    finally:
        await client.disconnect()

# واجهة المستخدم
st.title("📚 TeleBooks - محرك البحث عن الكتب")
st.markdown("ابحث عن الكتب في قنوات تيليجرام")

# مربع البحث
query = st.text_input("🔍 ابحث عن كتاب:", placeholder="أدخل اسم الكتاب أو المؤلف")

if st.button("بحث"):
    if query:
        with st.spinner("جاري البحث..."):
            try:
                results = asyncio.run(search_books(query))
                
                if results:
                    st.success(f"تم العثور على {len(results)} نتيجة")
                    
                    for result in results:
                        with st.expander(f"📖 {result['file_name']}"):
                            st.write(f"**القناة:** {result['channel']}")
                            st.write(f"**الوصف:** {result['text'][:200]}...")
                            st.write(f"**الحجم:** {result['size'] / (1024*1024):.2f} MB")
                            st.markdown(f"[فتح في تيليجرام](https://t.me/{result['channel'][1:]}/{result['message_id']})")
                else:
                    st.info("لم يتم العثور على نتائج")
            except Exception as e:
                st.error(f"حدث خطأ: {str(e)}")
    else:
        st.warning("الرجاء إدخال كلمة بحث")

# معلومات إضافية
st.sidebar.title("معلومات")
st.sidebar.info("""
هذا التطبيق يبحث في قنوات تيليجرام الشهيرة للكتب.
القنوات المدعومة:
- BooksThief
- librebook  
- pdfdrive
""")