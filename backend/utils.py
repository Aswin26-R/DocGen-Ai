import streamlit as st
import PyPDF2
import docx
import io
import arxiv
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

def initialize_session_state():
    """Initialize session state variables"""
    if 'documents' not in st.session_state:
        st.session_state.documents = []
    
    if 'summaries' not in st.session_state:
        st.session_state.summaries = []
    
    if 'quiz_history' not in st.session_state:
        st.session_state.quiz_history = []
    
    if 'activity_log' not in st.session_state:
        st.session_state.activity_log = []
    
    if 'current_quiz' not in st.session_state:
        st.session_state.current_quiz = None
    
    if 'quiz_state' not in st.session_state:
        st.session_state.quiz_state = {}

def log_activity(action: str):
    """Log user activity with timestamp"""
    activity = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'action': action,
        'user_id': st.session_state.get('user_id', 'anonymous')
    }
    st.session_state.activity_log.append(activity)
    
    # Keep only last 50 activities
    if len(st.session_state.activity_log) > 50:
        st.session_state.activity_log = st.session_state.activity_log[-50:]

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_file = io.BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    except Exception as e:
        st.error(f"Error extracting text from DOCX: {e}")
        return ""

def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from TXT file"""
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return file_bytes.decode('latin1')
        except Exception as e:
            st.error(f"Error reading text file: {e}")
            return ""

def process_uploaded_file(uploaded_file) -> Optional[Dict[str, Any]]:
    """Process uploaded file and extract text"""
    if not uploaded_file:
        return None
    
    file_bytes = uploaded_file.read()
    file_type = uploaded_file.type
    file_name = uploaded_file.name
    
    # Extract text based on file type
    text = ""
    if file_type == "application/pdf" or file_name.lower().endswith('.pdf'):
        text = extract_text_from_pdf(file_bytes)
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_name.lower().endswith('.docx'):
        text = extract_text_from_docx(file_bytes)
    elif file_type == "text/plain" or file_name.lower().endswith('.txt'):
        text = extract_text_from_txt(file_bytes)
    else:
        st.error(f"Unsupported file type: {file_type}")
        return None
    
    if not text.strip():
        st.error("No text could be extracted from the file.")
        return None
    
    # Create document record
    document = {
        'id': str(uuid.uuid4()),
        'title': file_name,
        'content': text,
        'type': 'uploaded',
        'file_type': file_type,
        'uploaded_at': datetime.now().isoformat(),
        'word_count': len(text.split()),
        'source': 'upload'
    }
    
    return document

def search_arxiv_papers(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search for papers on Arxiv"""
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        papers = []
        for result in client.results(search):
            paper = {
                'title': result.title,
                'authors': [author.name for author in result.authors],
                'abstract': result.summary,
                'url': result.entry_id,
                'pdf_url': result.pdf_url,
                'published': result.published.strftime('%Y-%m-%d'),
                'categories': result.categories
            }
            papers.append(paper)
        
        return papers
    except Exception as e:
        st.error(f"Error searching Arxiv: {e}")
        return []

def download_arxiv_paper(paper_url: str) -> Optional[Dict[str, Any]]:
    """Download and process Arxiv paper"""
    try:
        client = arxiv.Client()
        paper = next(client.results(arxiv.Search(id_list=[paper_url.split('/')[-1]])))
        
        # Download PDF
        pdf_path = paper.download_pdf(dirpath="./data/temp/")
        
        # Extract text from PDF
        with open(pdf_path, 'rb') as file:
            text = extract_text_from_pdf(file.read())
        
        # Clean up temp file
        import os
        os.remove(pdf_path)
        
        if not text.strip():
            return None
        
        # Create document record
        document = {
            'id': str(uuid.uuid4()),
            'title': paper.title,
            'content': text,
            'type': 'arxiv',
            'authors': [author.name for author in paper.authors],
            'abstract': paper.summary,
            'url': paper.entry_id,
            'published': paper.published.strftime('%Y-%m-%d'),
            'downloaded_at': datetime.now().isoformat(),
            'word_count': len(text.split()),
            'source': 'arxiv'
        }
        
        return document
    except Exception as e:
        st.error(f"Error downloading Arxiv paper: {e}")
        return None

def calculate_reading_time(word_count: int, wpm: int = 200) -> str:
    """Calculate estimated reading time"""
    minutes = word_count / wpm
    if minutes < 1:
        return "< 1 min"
    elif minutes < 60:
        return f"{int(minutes)} min"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}m"

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """Get document by ID"""
    for doc in st.session_state.documents:
        if doc['id'] == doc_id:
            return doc
    return None

def remove_document_by_id(doc_id: str) -> bool:
    """Remove document by ID"""
    for i, doc in enumerate(st.session_state.documents):
        if doc['id'] == doc_id:
            del st.session_state.documents[i]
            log_activity(f"Deleted document: {doc['title']}")
            return True
    return False
