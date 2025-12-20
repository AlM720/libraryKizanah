import streamlit as st
from telethon import TelegramClient
import asyncio
import os
import nest_asyncio  # لإدارة asyncio في Streamlit

nest_asyncio.apply()  # تطبيق لتجنب أخطاء الحلقات

# إعداد الصفحة
st.set_page_config(page_title="TeleBooks - تحميل الكتب", page_icon="📚")

# الحصول على بيانات API من secrets
api_id = int(st.secrets["api_id"])
api_hash = st.secrets["api_hash"]
bot_token = st.secrets["bot_token"]
channel_id = int(st.secrets["channel_id"])

# دالة للبحث عن الكتب باستخدام البوت
def search_books(query):
    results = []  # تعريف results مبكرًا لتجنب الخطأ
    try:
        # إنشاء حلقة حدث جديدة
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # تشغيل البحث
        client = TelegramClient("bot_session", api_id, api_hash)
        
        async def do_search():
            nonlocal results  # للوصول إلى results خارجيًا
            try:
                # تسجيل الدخول كبوت
                await client.start(bot_token=bot_token)
                
                st.info(f"🔍 جاري الاتصال بالقناة...")
                
                # الحصول على الكيان (القناة)
                entity = await client.get_entity(channel_id)
                
                st.info(f"✅ تم الاتصال! جاري سحب الرسائل...")
                
                # سحب الرسائل الأخيرة (بدون search لتجنب قيود البوت)
                messages = await client.get_messages(entity, limit=100)  # زد limit إذا لزم (مثل 500)
                
                st.info(f"📝 تم سحب {len(messages)} رسالة...")
                
                # فلترة يدوية بناءً على query
                for message in messages:
                    # التحقق من وجود ملف
                    if message.file:
                        file_name = message.file.name or message.text or 'ملف'
                        text_lower = (message.text or '').lower()
                        query_lower = query.lower()
                        
                        # فلتر إذا كانت query في النص أو اسم الملف
                        if query_lower in text_lower or query_lower in file_name.lower():
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
                    st.success(f"✅ وجدت {len(results)} نتيجة بعد الفلترة!")
                else:
                    st.warning("⚠️ لم يتم العثور على ملفات تطابق البحث في الرسائل الأخيرة")
                    
            except Exception as e:
                st.error(f"❌ خطأ: {str(e)}")
                st.info("💡 تأكد من: 1) البوت مشرف في القناة 2) channel_id صحيح (يبدأ بـ -100) 3) صلاحيات كافية")
            
            await client.disconnect()
        
        # تنفيذ البحث مع timeout
        loop.run_until_complete(asyncio.wait_for(do_search(), timeout=30))
        loop.close()
        
    except asyncio.TimeoutError:
        st.error("انتهت مهلة البحث. حاول مرة أخرى.")
    except Exception as e:
        st.error(f"حدث خطأ: {str(e)}")
    
    return results

# واجهة المستخدم (الباقي كما هو، مع تعديل زر البحث ليستخدم الدالة الجديدة)
st.title("📚 TeleBooks - محرك البحث عن الكتب")
st.markdown("ابحث عن الكتب في قناة تيليجرام")

# زر اختبار الاتصال (يبقى كما هو، لأنه يعمل مع البوت)
if st.button("🔧 اختبار اتصال البوت بالقناة"):
    with st.spinner("جاري الاختبار..."):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = TelegramClient("bot_session", api_id, api_hash)
            
            async def test_connection():
                await client.start(bot_token=bot_token)
                try:
                    entity = await client.get_entity(channel_id)
                    st.success(f"✅ تم الاتصال بالقناة: **{entity.title}**")
                    
                    messages = await client.get_messages(entity, limit=1)
                    if messages:
                        st.info(f"✅ يمكن قراءة الرسائل - آخر رسالة: {messages[0].date}")
                    
                    try:
                        test_msg = await client.send_message(entity, "🔧 اختبار البوت - سيتم الحذف")
                        st.success("✅ يمكن إرسال رسائل")
                        await client.delete_messages(entity, test_msg.id)
                        st.success("✅ يمكن حذف الرسائل")
                        st.success("🎉 البوت يعمل بشكل كامل!")
                    except Exception as e:
                        st.warning(f"⚠️ لا يمكن إرسال/حذف رسائل: {str(e)}")
                        st.info("💡 البوت يحتاج صلاحيات 'Post Messages' و 'Delete Messages'")
                except Exception as e:
                    st.error(f"❌ فشل الاختبار: {str(e)}")
                    st.warning("""
                    📌 تأكد من:
                    1. البوت مضاف كمشرف في القناة
                    2. channel_id صحيح (يبدأ بـ -100)
                    3. البوت لديه صلاحيات كافية
                    """)
                await client.disconnect()
            
            loop.run_until_complete(test_connection())
            loop.close()
        except Exception as e:
            st.error(f"❌ خطأ في الاختبار: {str(e)}")

st.markdown("---")

# مربع البحث
query = st.text_input("🔍 ابحث عن كتاب:", placeholder="أدخل اسم الكتاب أو المؤلف")

# تهيئة session state
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
                st.info("❌ لم يتم العثور على نتائج في الرسائل الأخيرة")
    else:
        st.warning("الرجاء إدخال كلمة بحث")

# عرض النتيجة الحالية (الباقي كما هو)
if st.session_state.results:
    result = st.session_state.results[st.session_state.current_index]
    
    st.markdown("---")
    st.subheader(f"📖 {result['file_name']}")
    st.write(f"**الوصف:** {result['text'][:300]}...")
    st.write(f"**الحجم:** {result['size'] / (1024*1024):.2f} MB")
    st.write(f"**التاريخ:** {result['date'].strftime('%Y-%m-%d %H:%M')}")
    
    channel_num = str(result.get('channel_id', channel_id)).replace('-100', '')
    st.markdown(f"### [📥 فتح في تيليجرام](https://t.me/c/{channel_num}/{result['message_id']})")
    
    st.info(f"النتيجة {st.session_state.current_index + 1} من {len(st.session_state.results)}")
    
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

# معلومات إضافية (الباقي كما هو)
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
- البحث محدود بالرسائل الأخيرة (يمكن زيادة الحد)
""")