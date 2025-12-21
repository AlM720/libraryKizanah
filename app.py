import streamlit as st
import asyncio
import time
from datetime import datetime

# تهيئة الصفحة
st.set_page_config(
    page_title="مكتبة الكزانة الرقمية",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS مخصص للتصميم الفاخر
st.markdown("""
<style>
    /* خلفية متدرجة فاخرة */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        color: #ffffff;
    }
    
    /* تنسيق الحاويات */
    .luxury-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 30px;
        margin: 20px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    /* أزرار فاخرة */
    .stButton > button {
        background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 15px 30px;
        border-radius: 50px;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* حقول الإدخال الأنيقة */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        color: white;
        padding: 15px;
        font-size: 16px;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.3);
    }
    
    /* عناوين أنيقة */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 300;
        letter-spacing: 2px;
    }
    
    /* رسائل النجاح والخطأ */
    .stSuccess {
        background: rgba(46, 204, 113, 0.2);
        border: 1px solid rgba(46, 204, 113, 0.5);
        border-radius: 10px;
        padding: 15px;
    }
    
    .stError {
        background: rgba(231, 76, 60, 0.2);
        border: 1px solid rgba(231, 76, 60, 0.5);
        border-radius: 10px;
        padding: 15px;
    }
</style>
""", unsafe_allow_html=True)

# تهيئة حالة الجلسة
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'admin_scan_completed' not in st.session_state:
    st.session_state.admin_scan_completed = False
if 'admin_duplicate_groups' not in st.session_state:
    st.session_state.admin_duplicate_groups = []
if 'admin_current_page' not in st.session_state:
    st.session_state.admin_current_page = 0
if 'search_results' not in st.session_state:
    st.session_state.search_results = None

# دالة عداد الثواني
def show_timer():
    if 'start_time' not in st.session_state:
        st.session_state.start_time = time.time()
    
    elapsed = int(time.time() - st.session_state.start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    
    st.markdown(f"""
        <div style="position: fixed; top: 10px; right: 10px; 
                    background: rgba(255,255,255,0.1); padding: 10px; 
                    border-radius: 20px; border: 1px solid rgba(255,255,255,0.2);">
            <span style="color: #667eea; font-weight: bold;">المدة:</span> 
            <span style="color: white;">{minutes:02d}:{seconds:02d}</span>
        </div>
    """, unsafe_allow_html=True)

# عرض العداد
show_timer()

# الواجهة الرئيسية
st.markdown("<h1 style='text-align: center; margin-bottom: 50px;'>مكتبة الكزانة الرقمية</h1>", unsafe_allow_html=True)

if st.session_state.is_admin:
    # واجهة المسؤول
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("خروج من وضع الإدارة", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    
    st.markdown("---")
    
    # مسح الملفات المكررة
    with st.container():
        st.markdown("<h3>نظام إدارة الملفات المتطابق</h3>", unsafe_allow_html=True)
        
        if not st.session_state.admin_scan_completed:
            st.markdown("<p style='text-align: center; margin: 30px 0;'>ابدأ عملية فحص المكتبة للكشف عن الملفات المتطابقة</p>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("بدء الفحص", use_container_width=True, type="primary"):
                    with st.spinner("جاري فحص المكتبة..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        duplicates = loop.run_until_complete(scan_for_duplicates())
                        loop.close()
                        
                        st.session_state.admin_duplicate_groups = duplicates
                        st.session_state.admin_scan_completed = True
                        st.session_state.admin_current_page = 0
                        st.rerun()
        else:
            total_groups = len(st.session_state.admin_duplicate_groups)
            
            if total_groups == 0:
                st.success("لا توجد ملفات متطابقة في المكتبة")
            else:
                st.info(f"تم العثور على {total_groups} مجموعة من الملفات المتطابقة")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("إعادة الفحص", use_container_width=True):
                    st.session_state.admin_scan_completed = False
                    st.session_state.admin_duplicate_groups = []
                    st.session_state.admin_current_page = 0
                    st.rerun()
            
            # عرض النتائج
            if total_groups > 0:
                page_size = 5
                start_idx = st.session_state.admin_current_page * page_size
                end_idx = start_idx + page_size
                displayed_groups = st.session_state.admin_duplicate_groups[start_idx:end_idx]
                
                for idx, group in enumerate(displayed_groups, start_idx + 1):
                    with st.expander(f"المجموعة {idx}: {len(group)} ملف متطابق", expanded=False):
                        for file_idx, file in enumerate(group, 1):
                            col1, col2, col3 = st.columns([3, 1, 1])
                            
                            with col1:
                                st.markdown(f"**{file['name']}**")
                                st.caption(f"الحجم: {file['size'] / (1024*1024):.2f} ميجابايت")
                            
                            with col2:
                                if st.button("فحص", key=f"check_{file['id']}"):
                                    pages = get_pdf_page_count(file['id'])
                                    if pages:
                                        st.success(f"{pages} صفحة")
                                    else:
                                        st.warning("غير متاح")
                            
                            with col3:
                                if st.button("حذف", key=f"delete_{file['id']}", type="secondary"):
                                    # طلب تأكيد الحذف
                                    st.warning(f"هل أنت متأكد من حذف: {file['name']}?")
                                    if st.button("تأكيد الحذف", key=f"confirm_{file['id']}"):
                                        with st.spinner("جاري الحذف..."):
                                            loop = asyncio.new_event_loop()
                                            asyncio.set_event_loop(loop)
                                            success = loop.run_until_complete(delete_file(file['id']))
                                            loop.close()
                                            
                                            if success:
                                                st.success("تم الحذف بنجاح")
                                                time.sleep(1)
                                                st.session_state.admin_scan_completed = False
                                                st.rerun()
                                            else:
                                                st.error("فشل الحذف")
                
                # التنقل بين الصفحات
                if total_groups > page_size:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.session_state.admin_current_page > 0:
                            if st.button("السابق", use_container_width=True):
                                st.session_state.admin_current_page -= 1
                                st.rerun()
                    
                    with col2:
                        st.markdown(f"<p style='text-align: center;'>صفحة {st.session_state.admin_current_page + 1} من {((total_groups - 1) // page_size) + 1}</p>", unsafe_allow_html=True)
                    
                    with col3:
                        if end_idx < total_groups:
                            if st.button("التالي", use_container_width=True):
                                st.session_state.admin_current_page += 1
                                st.rerun()

else:
    # واجهة المستخدم العادي
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='luxury-container'>", unsafe_allow_html=True)
        
        # دخول المسؤول
        with st.expander("دخول المسؤول", expanded=False):
            password = st.text_input("كلمة المرور:", type="password")
            if st.button("دخول", use_container_width=True):
                if password == st.secrets["admin_password"]:
                    st.session_state.is_admin = True
                    st.success("تم الدخول بنجاح")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("كلمة مرور خاطئة")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # البحث في الكتب
    st.markdown("<div class='luxury-container'>", unsafe_allow_html=True)
    st.markdown("<h3>البحث في المكتبة</h3>", unsafe_allow_html=True)
    
    query = st.text_input("ابحث عن كتاب أو موضوع:", placeholder="أدخل اسم الكتاب أو الكلمة المفتاحية")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("بحث", use_container_width=True, type="primary"):
            if query:
                with st.spinner("جاري البحث..."):
                    results = search_books_async(query)
                    st.session_state.search_results = results
                    st.session_state.search_time = time.time()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # عرض نتائج البحث
    if st.session_state.search_results:
        st.markdown("<div class='luxury-container'>", unsafe_allow_html=True)
        
        if st.session_state.search_results:
            st.markdown(f"<h4>نتائج البحث: {len(st.session_state.search_results)} كتاب</h4>", unsafe_allow_html=True)
            
            for book in st.session_state.search_results:
                with st.expander(f"📖 {book.get('title', 'كتاب')}", expanded=False):
                    st.markdown(f"**المؤلف:** {book.get('author', 'غير متاح')}")
                    st.markdown(f"**السنة:** {book.get('year', 'غير متاح')}")
                    st.markdown(f"**الوصف:** {book.get('description', 'لا يوجد وصف')}")
        else:
            st.info("لم يتم العثور على نتائج")
        
        st.markdown("</div>", unsafe_allow_html=True)

# دوال وهمية للتوافق (يجب استبدالها بالدوال الفعلية)
def search_books_async(query):
    # هذه دالة وهمية يجب استبدالها بالدالة الفعلية
    return []

def scan_for_duplicates():
    # هذه دالة وهمية يجب استبدالها بالدالة الفعلية
    return []

def get_pdf_page_count(file_id):
    # هذه دالة وهمية يجب استبدالها بالدالة الفعلية
    return None

def delete_file(file_id):
    # هذه دالة وهمية يجب استبدالها بالدالة الفعلية
    return False
