import streamlit as st
import os
from backend.auth import check_authentication, render_login
from backend.utils import initialize_session_state

# Page configuration
st.set_page_config(
    page_title="DocGen - AI Documentation & Learning Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schema on first run
try:
    from backend.database import Database
    db = Database()
    db.init_schema()
except Exception as e:
    st.warning(f"Database initialization: {str(e)[:100]}. Using session-only storage.")

# Initialize session state
initialize_session_state()

# Authentication check
if not check_authentication():
    render_login()
    st.stop()

# Main application
st.title("🎓 DocGen - AI Documentation & Learning Assistant")
st.markdown("---")

# Welcome message
st.markdown("""
### Welcome to DocGen! 👋

Transform your documents and academic papers into interactive learning experiences with AI-powered:
- **📚 Document Library**: Upload PDFs, DOCX, TXT files or search Arxiv papers
- **🧠 Quiz Center**: Generate multiple choice quizzes and sentence completion exercises
- **📝 Summaries**: Create concise, markdown-formatted summaries
- **📊 Dashboard**: Track your learning progress and performance

**Get Started:**
1. Navigate to the Document Library to upload your first document
2. Generate learning materials from your uploaded content
3. Track your progress in the Dashboard

---
""")

# Quick stats
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📄 Documents",
        value=len(st.session_state.get('documents', []))
    )

with col2:
    st.metric(
        label="📝 Summaries",
        value=len(st.session_state.get('summaries', []))
    )

with col3:
    st.metric(
        label="🎯 Quizzes Taken",
        value=len(st.session_state.get('quiz_history', []))
    )

with col4:
    avg_score = 0
    if st.session_state.get('quiz_history'):
        scores = [q.get('score', 0) for q in st.session_state.quiz_history]
        avg_score = sum(scores) / len(scores)
    st.metric(
        label="📈 Avg Score",
        value=f"{avg_score:.1f}%"
    )

# Recent activity
st.subheader("📅 Recent Activity")
if st.session_state.get('activity_log'):
    for activity in st.session_state.activity_log[-5:]:
        st.info(f"**{activity['timestamp']}** - {activity['action']}")
else:
    st.info("No recent activity. Start by uploading a document!")

# Quick actions
st.subheader("🚀 Quick Actions")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📤 Upload Document", use_container_width=True):
        st.switch_page("pages/1_📚_Document_Library.py")

with col2:
    if st.button("🎯 Take Quiz", use_container_width=True):
        st.switch_page("pages/2_🧠_Quiz_Center.py")

with col3:
    if st.button("📊 View Dashboard", use_container_width=True):
        st.switch_page("pages/4_📊_Dashboard.py")
