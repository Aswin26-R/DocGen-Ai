import streamlit as st
import os
from backend.auth import check_authentication, render_logout_button
from backend.utils import (
    initialize_session_state, process_uploaded_file, search_arxiv_papers,
    download_arxiv_paper, log_activity, get_document_by_id, remove_document_by_id,
    calculate_reading_time
)
from backend.embeddings import DocumentEmbeddings

# Page configuration
st.set_page_config(
    page_title="Document Library - DocGen",
    page_icon="📚",
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

# Initialize embeddings
@st.cache_resource
def get_embeddings():
    return DocumentEmbeddings()

embeddings = get_embeddings()

st.title("📚 Document Library")
st.markdown("Upload documents or search Arxiv papers to build your learning library.")

# Tabs for different actions
tab1, tab2, tab3 = st.tabs(["📤 Upload Documents", "🔍 Search Arxiv", "📋 My Documents"])

with tab1:
    st.subheader("Upload Your Documents")
    st.markdown("Support formats: PDF, DOCX, TXT")
    
    uploaded_files = st.file_uploader(
        "Choose files",
        accept_multiple_files=True,
        type=['pdf', 'docx', 'txt'],
        help="Upload PDF, DOCX, or TXT files to add to your library"
    )
    
    if uploaded_files:
        if st.button("📥 Process Uploaded Files", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            processed_count = 0
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing: {uploaded_file.name}")
                
                # Process file
                document = process_uploaded_file(uploaded_file)
                
                if document:
                    # Add to session state
                    st.session_state.documents.append(document)
                    
                    # Save to database
                    from backend.database import Database
                    if st.session_state.get('user_id'):
                        try:
                            db = Database()
                            db.save_document(st.session_state.user_id, document)
                        except:
                            pass
                    
                    # Add to vector store
                    embeddings.add_document(
                        document['content'],
                        {
                            'document_id': document['id'],
                            'title': document['title'],
                            'type': document['type'],
                            'source': document['source']
                        }
                    )
                    
                    processed_count += 1
                    log_activity(f"Uploaded document: {document['title']}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.text(f"✅ Processed {processed_count} documents successfully!")
            
            if processed_count > 0:
                st.success(f"Added {processed_count} documents to your library!")
                st.rerun()

with tab2:
    st.subheader("Search Academic Papers")
    st.markdown("Search and import papers from Arxiv")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        arxiv_query = st.text_input(
            "Search query",
            placeholder="e.g., machine learning, neural networks, quantum computing",
            help="Enter keywords to search for papers on Arxiv"
        )
    with col2:
        max_results = st.selectbox("Max results", [5, 10, 15, 20], index=1)
    
    if arxiv_query and st.button("🔍 Search Arxiv", type="primary"):
        with st.spinner("Searching Arxiv..."):
            papers = search_arxiv_papers(arxiv_query, max_results)
        
        if papers:
            st.success(f"Found {len(papers)} papers")
            
            for i, paper in enumerate(papers):
                with st.expander(f"📄 {paper['title'][:100]}..."):
                    st.markdown(f"**Authors:** {', '.join(paper['authors'])}")
                    st.markdown(f"**Published:** {paper['published']}")
                    st.markdown(f"**Categories:** {', '.join(paper['categories'])}")
                    st.markdown(f"**Abstract:** {paper['abstract'][:300]}...")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"📥 Download Paper", key=f"download_{i}"):
                            with st.spinner("Downloading and processing..."):
                                document = download_arxiv_paper(paper['url'])
                            
                            if document:
                                # Add to session state
                                st.session_state.documents.append(document)
                                
                                # Save to database
                                from backend.database import Database
                                if st.session_state.get('user_id'):
                                    try:
                                        db = Database()
                                        db.save_document(st.session_state.user_id, document)
                                    except:
                                        pass
                                
                                # Add to vector store
                                embeddings.add_document(
                                    document['content'],
                                    {
                                        'document_id': document['id'],
                                        'title': document['title'],
                                        'type': document['type'],
                                        'source': document['source']
                                    }
                                )
                                
                                log_activity(f"Downloaded paper: {document['title']}")
                                st.success("Paper added to your library!")
                                st.rerun()
                            else:
                                st.error("Failed to download paper")
                    
                    with col2:
                        st.link_button("🔗 View on Arxiv", paper['url'])
        else:
            st.info("No papers found. Try different keywords.")

with tab3:
    st.subheader("My Document Library")
    
    if not st.session_state.documents:
        st.info("No documents in your library yet. Upload some documents or search Arxiv papers!")
    else:
        # Library stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 Total Documents", len(st.session_state.documents))
        with col2:
            total_words = sum(doc.get('word_count', 0) for doc in st.session_state.documents)
            st.metric("📝 Total Words", f"{total_words:,}")
        with col3:
            reading_time = calculate_reading_time(total_words)
            st.metric("⏱️ Reading Time", reading_time)
        
        st.markdown("---")
        
        # Search within library
        search_query = st.text_input(
            "🔍 Search your documents",
            placeholder="Search by title or content...",
            help="Search through your document library"
        )
        
        if search_query:
            with st.spinner("Searching..."):
                results = embeddings.search(search_query, k=10)
            
            if results:
                st.success(f"Found {len(results)} relevant documents")
                for result in results:
                    doc = get_document_by_id(result['document_id'])
                    if doc:
                        with st.expander(f"📄 {doc['title']} (Score: {result['similarity_score']:.2f})"):
                            st.markdown(f"**Type:** {doc['type'].title()}")
                            st.markdown(f"**Words:** {doc.get('word_count', 0):,}")
                            st.markdown(f"**Content Preview:** {result['text'][:200]}...")
            else:
                st.info("No documents found matching your search.")
        
        # Document list
        st.subheader("All Documents")
        
        for doc in st.session_state.documents:
            with st.expander(f"📄 {doc['title']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Type:** {doc['type'].title()}")
                    st.markdown(f"**Words:** {doc.get('word_count', 0):,}")
                    st.markdown(f"**Added:** {doc.get('uploaded_at', doc.get('downloaded_at', 'Unknown'))[:10]}")
                    
                    if doc.get('authors'):
                        st.markdown(f"**Authors:** {', '.join(doc['authors'])}")
                    
                    # Content preview
                    preview = doc['content'][:300]
                    st.markdown(f"**Preview:** {preview}...")
                
                with col2:
                    # Action buttons
                    if st.button(f"📝 Summarize", key=f"sum_{doc['id']}"):
                        st.session_state.selected_doc_for_summary = doc['id']
                        st.switch_page("pages/3_📝_Summaries.py")
                    
                    if st.button(f"🧠 Create Quiz", key=f"quiz_{doc['id']}"):
                        st.session_state.selected_doc_for_quiz = doc['id']
                        st.switch_page("pages/2_🧠_Quiz_Center.py")
                    
                    if st.button(f"🗑️ Delete", key=f"del_{doc['id']}", type="secondary"):
                        if remove_document_by_id(doc['id']):
                            embeddings.remove_document(doc['id'])
                            # Delete from database
                            from backend.database import Database
                            if st.session_state.get('user_id'):
                                try:
                                    db = Database()
                                    db.delete_document(st.session_state.user_id, doc['id'])
                                except:
                                    pass
                            st.success("Document deleted!")
                            st.rerun()

# Vector store statistics
with st.sidebar:
    st.subheader("📊 Library Stats")
    stats = embeddings.get_document_stats()
    st.metric("Vector Chunks", stats['total_chunks'])
    st.metric("Indexed Documents", stats['total_documents'])
    st.metric("Search Index Size", stats['index_size'])
