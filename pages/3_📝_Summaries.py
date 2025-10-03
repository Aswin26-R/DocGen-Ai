import streamlit as st
from backend.auth import check_authentication, render_logout_button
from backend.utils import initialize_session_state, log_activity, get_document_by_id
from backend.orchestrator import AIOrchestrator
from datetime import datetime
import uuid

# Page configuration
st.set_page_config(
    page_title="Summaries - DocGen",
    page_icon="📝",
    layout="wide"
)

# Authentication check
if not check_authentication():
    st.error("Please log in from the main page first.")
    st.stop()

# Initialize session state
initialize_session_state()

# Render logout button
render_logout_button()

# Initialize AI orchestrator
@st.cache_resource
def get_orchestrator():
    return AIOrchestrator()

try:
    orchestrator = get_orchestrator()
except ValueError as e:
    st.error(f"AI Service Error: {e}")
    st.stop()

st.title("📝 Document Summaries")
st.markdown("Generate AI-powered summaries of your documents with markdown formatting.")

# Check if a document was selected for summary
selected_doc_id = st.session_state.get('selected_doc_for_summary')

if not st.session_state.documents:
    st.warning("No documents in your library. Please upload documents first.")
    if st.button("📚 Go to Document Library"):
        st.switch_page("pages/1_📚_Document_Library.py")
    st.stop()

# Tabs for different summary functions
tab1, tab2 = st.tabs(["📄 Generate Summary", "📚 Summary Library"])

with tab1:
    st.subheader("Generate New Summary")
    
    # Document selection
    doc_options = {doc['title']: doc['id'] for doc in st.session_state.documents}
    
    # Pre-select document if coming from library
    default_index = 0
    if selected_doc_id and selected_doc_id in doc_options.values():
        doc_titles = list(doc_options.keys())
        doc_ids = list(doc_options.values())
        default_index = doc_ids.index(selected_doc_id)
    
    selected_title = st.selectbox(
        "Select Document to Summarize",
        options=list(doc_options.keys()),
        index=default_index,
        help="Choose a document from your library to generate a summary"
    )
    
    selected_doc = get_document_by_id(doc_options[selected_title])
    
    if selected_doc:
        # Document preview
        with st.expander("📖 Document Preview"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Word Count", f"{selected_doc.get('word_count', 0):,}")
            with col2:
                st.metric("Type", selected_doc['type'].title())
            with col3:
                if selected_doc.get('authors'):
                    st.write(f"**Authors:** {', '.join(selected_doc['authors'])}")
            
            # Content preview
            preview_text = selected_doc['content'][:500]
            st.markdown(f"**Content Preview:**\n\n{preview_text}...")
        
        # Summary options
        st.subheader("Summary Options")
        
        col1, col2 = st.columns(2)
        with col1:
            summary_style = st.selectbox(
                "Summary Style",
                ["Comprehensive", "Bullet Points", "Executive Summary", "Study Notes"],
                help="Choose the style of summary you prefer"
            )
        
        with col2:
            include_concepts = st.checkbox(
                "Include Key Concepts",
                value=True,
                help="Extract and highlight key concepts and terms"
            )
        
        # Generate summary button
        if st.button("✨ Generate Summary", type="primary", use_container_width=True):
            with st.spinner("Generating summary... This may take a moment."):
                try:
                    # Create custom prompt based on options
                    style_prompts = {
                        "Comprehensive": "Create a comprehensive, detailed summary",
                        "Bullet Points": "Create a summary using bullet points and clear structure",
                        "Executive Summary": "Create an executive summary focusing on key insights",
                        "Study Notes": "Create study-friendly notes with important points highlighted"
                    }
                    
                    style_instruction = style_prompts.get(summary_style, "Create a comprehensive summary")
                    
                    # Generate the summary
                    summary_text = orchestrator.generate_summary(
                        selected_doc['content'],
                        selected_doc['title']
                    )
                    
                    if summary_text and "Error" not in summary_text:
                        # Extract key concepts if requested
                        key_concepts = []
                        if include_concepts:
                            key_concepts = orchestrator.extract_key_concepts(selected_doc['content'])
                        
                        # Create summary record
                        summary_record = {
                            'id': str(uuid.uuid4()),
                            'document_id': selected_doc['id'],
                            'document_title': selected_doc['title'],
                            'summary': summary_text,
                            'style': summary_style,
                            'key_concepts': key_concepts,
                            'created_at': datetime.now().isoformat(),
                            'word_count': len(summary_text.split())
                        }
                        
                        # Add to session state
                        st.session_state.summaries.append(summary_record)
                        
                        # Save to database
                        from backend.database import Database
                        if st.session_state.get('user_id'):
                            try:
                                db = Database()
                                db.save_summary(st.session_state.user_id, summary_record)
                            except:
                                pass
                        
                        # Log activity
                        log_activity(f"Generated summary for: {selected_doc['title']}")
                        
                        st.success("✅ Summary generated successfully!")
                        
                        # Display the summary
                        st.markdown("---")
                        st.subheader(f"📄 Summary: {selected_doc['title']}")
                        
                        # Summary metadata
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Summary Length", f"{len(summary_text.split())} words")
                        with col2:
                            st.metric("Style", summary_style)
                        with col3:
                            st.metric("Concepts", len(key_concepts))
                        
                        # Display key concepts if available
                        if key_concepts:
                            st.subheader("🔑 Key Concepts")
                            concept_cols = st.columns(min(3, len(key_concepts)))
                            for i, concept in enumerate(key_concepts[:6]):  # Show first 6 concepts
                                with concept_cols[i % 3]:
                                    st.info(concept)
                        
                        # Display the summary content
                        st.subheader("📝 Summary Content")
                        st.markdown(summary_text)
                        
                        # Download option
                        st.download_button(
                            "💾 Download Summary",
                            data=f"# {selected_doc['title']}\n\n## Summary\n\n{summary_text}\n\n## Key Concepts\n\n{', '.join(key_concepts)}",
                            file_name=f"summary_{selected_doc['title'][:30]}.md",
                            mime="text/markdown",
                            help="Download summary as markdown file"
                        )
                        
                        # Clear the selected document
                        if 'selected_doc_for_summary' in st.session_state:
                            del st.session_state.selected_doc_for_summary
                    
                    else:
                        st.error("Failed to generate summary. Please try again.")
                
                except Exception as e:
                    st.error(f"Error generating summary: {e}")

with tab2:
    st.subheader("Summary Library")
    
    if not st.session_state.summaries:
        st.info("No summaries generated yet. Create your first summary using the 'Generate Summary' tab!")
    else:
        # Summary statistics
        total_summaries = len(st.session_state.summaries)
        total_summary_words = sum(s.get('word_count', 0) for s in st.session_state.summaries)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📝 Total Summaries", total_summaries)
        with col2:
            st.metric("📊 Total Words", f"{total_summary_words:,}")
        with col3:
            avg_length = total_summary_words // total_summaries if total_summaries > 0 else 0
            st.metric("📏 Avg Length", f"{avg_length} words")
        
        st.markdown("---")
        
        # Search summaries
        search_term = st.text_input(
            "🔍 Search Summaries",
            placeholder="Search by document title or content...",
            help="Search through your summary library"
        )
        
        # Filter summaries
        filtered_summaries = st.session_state.summaries
        if search_term:
            filtered_summaries = [
                s for s in st.session_state.summaries
                if search_term.lower() in s['document_title'].lower() or 
                   search_term.lower() in s['summary'].lower()
            ]
        
        # Display summaries
        for summary in reversed(filtered_summaries):  # Most recent first
            with st.expander(f"📄 {summary['document_title']} - {summary['created_at'][:10]}"):
                # Summary metadata
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"**Style:** {summary['style']}")
                with col2:
                    st.markdown(f"**Length:** {summary.get('word_count', 0)} words")
                with col3:
                    st.markdown(f"**Created:** {summary['created_at'][:10]}")
                with col4:
                    st.markdown(f"**Concepts:** {len(summary.get('key_concepts', []))}")
                
                # Key concepts
                if summary.get('key_concepts'):
                    st.markdown("**🔑 Key Concepts:**")
                    concepts_text = " • ".join(summary['key_concepts'][:8])  # First 8 concepts
                    st.markdown(f"*{concepts_text}*")
                
                # Summary content
                st.markdown("**📝 Summary:**")
                st.markdown(summary['summary'])
                
                # Action buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    # Download button
                    st.download_button(
                        "💾 Download",
                        data=f"# {summary['document_title']}\n\n## Summary\n\n{summary['summary']}\n\n## Key Concepts\n\n{', '.join(summary.get('key_concepts', []))}",
                        file_name=f"summary_{summary['document_title'][:30]}.md",
                        mime="text/markdown",
                        key=f"download_{summary['id']}"
                    )
                
                with col2:
                    # Create quiz from summary
                    if st.button("🧠 Create Quiz", key=f"quiz_{summary['id']}"):
                        # Find the original document
                        orig_doc = get_document_by_id(summary['document_id'])
                        if orig_doc:
                            st.session_state.selected_doc_for_quiz = orig_doc['id']
                            st.switch_page("pages/2_🧠_Quiz_Center.py")
                        else:
                            st.error("Original document not found")
                
                with col3:
                    # Delete summary
                    if st.button("🗑️ Delete", key=f"delete_{summary['id']}", type="secondary"):
                        # Remove from summaries
                        st.session_state.summaries = [s for s in st.session_state.summaries if s['id'] != summary['id']]
                        # Delete from database
                        from backend.database import Database
                        if st.session_state.get('user_id'):
                            try:
                                db = Database()
                                db.delete_summary(st.session_state.user_id, summary['id'])
                            except:
                                pass
                        log_activity(f"Deleted summary for: {summary['document_title']}")
                        st.success("Summary deleted!")
                        st.rerun()

# Sidebar with summary tips
with st.sidebar:
    st.markdown("### 💡 Summary Tips")
    st.markdown("""
    **Best Practices:**
    - Longer documents create more detailed summaries
    - Use 'Key Concepts' for study materials
    - Executive summaries work well for research papers
    - Bullet points are great for quick reference
    
    **Summary Styles:**
    - **Comprehensive**: Detailed, paragraph format
    - **Bullet Points**: Structured, easy to scan
    - **Executive**: High-level insights
    - **Study Notes**: Learning-focused
    """)
