import streamlit as st
from telethon import TelegramClient
import asyncio
import os

# إعداد الصفحة
st.set_page_config(page_title="TeleBooks - تحميل الكتب", page_icon="📚")

# الحصول على بيانات API من secrets
api_id = st.secrets["api_id"]
api_hash = st.secrets["api_hash"]
bot_token = st.secrets["bot_token"]
channel_id = st.secrets["channel_id"]

# دالة للبحث عن الكتب
def search_books(query):
    try:
        # إنشاء حلقة حدث جديدة
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # تشغيل البحث
        client = TelegramClient("bot_session", api_id, api_hash)
        
        async def do_search():
            # استخدام bot_token للدخول
            await client.start(bot_token=bot_token)
            results = []
            
            try:
                st.info(f"🔍 جاري الاتصال بالقناة...")
                
                # محاولة الحصول على القناة
                # إذا كان channel_id رقم، استخدمه مباشرة
                # إذا كان رابط دعوة، استخدم hash الدعوة
                try:
                    # محاولة استخدامه كرقم أولاً
                    entity = await client.get_entity(int(channel_id))
                except ValueError:
                    # إذا لم ينجح، جرب استخدامه كما هو (قد يكون username أو link)
                    entity = await client.get_entity(channel_id)
                
                st.info(f"✅ تم الاتصال! جاري البحث...")
                
                # البحث في رسائل القناة
                messages = await client.get_messages(entity, limit=100, search=query)
                
                st.info(f"📝 تم فحص {len(messages)} رسالة...")
                
                for message in messages:
                    # التحقق من وجود ملف
                    if message.file:
                        file_name = message.file.name or message.text or 'ملف'
                        
                        # قبول جميع أنواع الملفات
                        results.append({
                            'channel': f"القناة المحددة",
                            'message_id': message.id,
                            'text': message.text or 'بدون وصف',
                            'file_name': file_name,
                            'size': message.file.size or 0,
                            'date': message.date,
                            'channel_id': entity.id
                        })
                
                if results:
                    st.success(f"✅ وجدت {len(results)} نتيجة!")
                else:
                    st.warning("⚠️ لم يتم العثور على ملفات بهذا الاسم")
                    
            except Exception as e:
                st.error(f"❌ خطأ: {str(e)}")
                st.info("💡 تأكد من: 1) البوت مضاف للقناة كـ Admin  2) channel_id صحيح")
            
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
st.markdown("ابحث عن الكتب في قناة تيليجرام")

# مربع البحث
query = st.text_input("🔍 ابحث عن كتاب:", placeholder="أدخل اسم الكتاب أو المؤلف")

# تهيئة session state لتتبع النتائج والصفحة الحالية
if 'results' not in st.session_state:
    st.session_state.results = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

if st.button("بحث"):
    if query:
        with st.spinner("جاري البحث في القناة..."):
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
    st.write(f"**الوصف:** {result['text'][:300]}...")
    st.write(f"**الحجم:** {result['size'] / (1024*1024):.2f} MB")
    st.write(f"**التاريخ:** {result['date'].strftime('%Y-%m-%d %H:%M')}")
    
    # رابط مباشر للرسالة (يعمل مع القنوات الخاصة)
    channel_num = str(result.get('channel_id', channel_id)).replace('-100', '')
    st.markdown(f"### [📥 فتح في تيليجرام](https://t.me/c/{channel_num}/{result['message_id']})")
    
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
هذا التطبيق يبحث في قناة تيليجرام محددة.

📚 **كيفية الاستخدام:**
1. اكتب اسم الكتاب الذي تبحث عنه
2. اضغط على زر "بحث"
3. انتظر قليلاً حتى تظهر النتائج
4. استخدم "التالي" و "السابق" للتنقل

💡 **نصائح:**
- ابحث باسم الكتاب أو المؤلف
- جرب كلمات مفتاحية مختلفة
- يشمل جميع أنواع الملفات (PDF, DOC, ZIP, EPUB, إلخ)
""")