# DocGen - AI Documentation & Learning Assistant

## Overview

DocGen is a full-stack AI-powered learning platform that transforms documents and academic papers into interactive learning experiences. Users upload documents (PDF, DOCX, TXT) or fetch papers from Arxiv, then generate AI-powered quizzes, summaries, and Q&A exercises. The application provides progress tracking and performance analytics to help users optimize their learning journey.

**Core Value Proposition:** Convert static documents into interactive, AI-enhanced learning materials with automated quiz generation, smart summaries, and progress tracking.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Framework:** Streamlit multi-page application
- **Main Entry:** `app.py` serves as the authentication gateway and home page
- **Page Structure:** Multi-page app using Streamlit's `pages/` directory pattern
  - Document Library (page 1): Document upload, Arxiv integration, library management
  - Quiz Center (page 2): Multiple choice, sentence completion, Q&A exercises
  - Summaries (page 3): AI summary generation and library
  - Dashboard (page 4): Analytics, performance metrics, activity visualization
  - Document Tools (page 5): Document comparison and cross-referencing

**Rationale:** Streamlit chosen for rapid prototyping and built-in session management, eliminating need for complex frontend framework. Multi-page structure provides clear feature separation while maintaining shared session state.

### Backend Architecture

**Modular Backend Design** (`backend/` directory):

1. **Authentication System** (`auth.py`)
   - API key-based authentication using Google Gemini API key
   - Session-based user identification via hashed API keys
   - No traditional username/password - API key serves as both credential and service access
   - **Decision:** Simplified auth model where API key validates both user identity and AI service access

2. **AI Orchestration** (`orchestrator.py`)
   - LangChain-style patterns using Google Gemini API directly
   - Content generation pipeline: summaries, MCQ quizzes, sentence completion, Q&A evaluation
   - Model: `gemini-2.5-flash` for cost-effective generation
   - **Decision:** Direct Gemini API usage instead of full LangChain to reduce dependencies while maintaining pipeline patterns

3. **Vector Search & Embeddings** (`embeddings.py`)
   - FAISS-based local vector storage for document search
   - Gemini embeddings API (768 dimensions)
   - Text chunking strategy: 512 tokens with 50-token overlap
   - Fallback to keyword search when embeddings unavailable
   - **Decision:** Local FAISS storage for simplicity; can be migrated to cloud vector DB later

4. **Data Persistence** (`database.py`)
   - PostgreSQL for structured data (documents, summaries, quiz history, activity logs)
   - Schema: Separate tables for documents, summaries, quiz sessions, activity tracking
   - Graceful degradation: Falls back to session-only storage if DB unavailable
   - **Decision:** PostgreSQL for relational data with JSON support for metadata flexibility

5. **Utility Functions** (`utils.py`)
   - File processing: PDF (PyPDF2), DOCX (python-docx), TXT
   - Arxiv integration for academic paper import
   - Session state initialization and management
   - Activity logging

### Data Flow Architecture

**Session State Management:**
- Streamlit session_state as primary runtime storage
- Database backing for persistence across sessions
- User-scoped data isolation via hashed API key user_id
- Lazy loading: DB queries only when user authenticated

**Content Generation Pipeline:**
1. Document upload → Text extraction → Chunking → Embedding generation → FAISS storage
2. User request → Context retrieval → Prompt construction → Gemini API → Response processing
3. Quiz/Summary → User interaction → Score calculation → Activity logging → Dashboard metrics

**Fallback Strategy:**
- Database connection failure → Session-only mode
- Embedding service unavailable → Keyword search fallback
- API errors → User-friendly error messages with partial functionality

### Design Patterns

1. **Separation of Concerns:** Backend modules isolated by function (auth, AI, embeddings, data)
2. **Resource Caching:** `@st.cache_resource` for expensive initializations (AI orchestrator)
3. **Progressive Enhancement:** Core features work without database; enhanced features require DB
4. **Stateful Pages:** Each page checks authentication and initializes required state independently

## External Dependencies

### AI & Machine Learning
- **Google Gemini API** (`google-generativeai`): Primary LLM for content generation, quiz creation, and evaluation
- **sentence-transformers** (via Gemini): Embedding generation for semantic search
- **FAISS** (`faiss-cpu`): Local vector similarity search and document retrieval

### Document Processing
- **PyPDF2**: PDF text extraction
- **python-docx**: DOCX file processing
- **arxiv**: Academic paper search and download from Arxiv API

### Data & Storage
- **PostgreSQL** (`psycopg2`): Primary relational database
  - Schema: documents, summaries, quiz_history, activity_log tables
  - Requires `DATABASE_URL` environment variable
- **FAISS index files**: Pickled embeddings stored in `data/embeddings_index.pkl`

### Visualization & Analytics
- **Plotly** (`plotly`): Interactive charts for dashboard metrics
- **Pandas**: Data manipulation for analytics

### Framework & Authentication
- **Streamlit**: Web application framework with built-in session management
- **hashlib**: API key hashing for user identification (Python standard library)

### Environment Configuration
- **Required Environment Variables:**
  - `DATABASE_URL`: PostgreSQL connection string
  - `GEMINI_API_KEY`: Optional fallback if not provided via UI
- **Session Storage:**
  - `gemini_api_key`: User's API key (runtime only, not persisted)
  - `user_id`: Hashed API key (first 12 characters)
  - `authenticated`: Boolean authentication state

### Deployment Considerations
- Platform: Replit (primary) with local development support
- Storage: Local FAISS files + PostgreSQL database
- Secrets management: Streamlit secrets or environment variables
- No Auth0 integration despite initial specs (simplified to API key auth)