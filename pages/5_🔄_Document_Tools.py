import streamlit as st
import google.generativeai as genai
from backend.auth import check_authentication, render_logout_button
from backend.utils import initialize_session_state, get_document_by_id
from backend.orchestrator import AIOrchestrator

# Page configuration
st.set_page_config(
    page_title="Document Tools - DocGen",
    page_icon="🔄",
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

st.title("🔄 Document Tools")
st.markdown("Compare documents and find cross-references across your library.")

if not st.session_state.documents or len(st.session_state.documents) < 2:
    st.warning("You need at least 2 documents to use these tools. Please upload more documents.")
    if st.button("📚 Go to Document Library"):
        st.switch_page("pages/1_📚_Document_Library.py")
    st.stop()

# Tabs for different tools
tab1, tab2 = st.tabs(["📊 Document Comparison", "🔗 Cross-References"])

with tab1:
    st.subheader("Compare Two Documents")
    st.markdown("Select two documents to compare their content, themes, and differences.")
    
    # Document selection
    col1, col2 = st.columns(2)
    
    doc_options = {doc['title']: doc['id'] for doc in st.session_state.documents}
    
    with col1:
        st.markdown("**📄 First Document**")
        doc1_title = st.selectbox(
            "Select first document",
            options=list(doc_options.keys()),
            key="doc1"
        )
        doc1 = get_document_by_id(doc_options[doc1_title])
        
        if doc1:
            st.info(f"**Words:** {doc1.get('word_count', 0):,}")
            st.text_area("Preview", doc1['content'][:300] + "...", height=150, disabled=True, key="preview1")
    
    with col2:
        st.markdown("**📄 Second Document**")
        doc2_title = st.selectbox(
            "Select second document",
            options=list(doc_options.keys()),
            key="doc2"
        )
        doc2 = get_document_by_id(doc_options[doc2_title])
        
        if doc2:
            st.info(f"**Words:** {doc2.get('word_count', 0):,}")
            st.text_area("Preview", doc2['content'][:300] + "...", height=150, disabled=True, key="preview2")
    
    # Comparison options
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        comparison_type = st.selectbox(
            "Comparison Type",
            ["Similarities & Differences", "Thematic Analysis", "Content Summary", "Key Insights"]
        )
    with col2:
        detail_level = st.select_slider(
            "Detail Level",
            options=["Brief", "Moderate", "Detailed"],
            value="Moderate"
        )
    
    if st.button("🔍 Compare Documents", type="primary", use_container_width=True):
        if doc1['id'] == doc2['id']:
            st.error("Please select two different documents to compare.")
        else:
            with st.spinner("Analyzing documents..."):
                # Create comparison prompt
                prompt = f"""
                Compare the following two documents and provide a {comparison_type.lower()} analysis.
                Detail level: {detail_level}
                
                Document 1: {doc1['title']}
                Content: {doc1['content'][:2000]}...
                
                Document 2: {doc2['title']}
                Content: {doc2['content'][:2000]}...
                
                Please provide:
                1. Main similarities between the documents
                2. Key differences in content and approach
                3. Unique insights from each document
                4. Synthesis of both documents
                
                Format your response in clear markdown with headers and bullet points.
                """
                
                try:
                    response = orchestrator.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    
                    if response.text:
                        st.markdown("---")
                        st.subheader(f"📊 Comparison: {doc1['title']} vs {doc2['title']}")
                        st.markdown(response.text)
                        
                        # Export option
                        export_text = f"# Document Comparison\n\n"
                        export_text += f"## Documents\n"
                        export_text += f"- **Document 1:** {doc1['title']}\n"
                        export_text += f"- **Document 2:** {doc2['title']}\n\n"
                        export_text += f"## Analysis Type: {comparison_type}\n\n"
                        export_text += response.text
                        
                        st.download_button(
                            "💾 Download Comparison",
                            data=export_text,
                            file_name=f"comparison_{doc1['title'][:20]}_{doc2['title'][:20]}.md",
                            mime="text/markdown"
                        )
                    else:
                        st.error("Failed to generate comparison.")
                        
                except Exception as e:
                    st.error(f"Error generating comparison: {e}")

with tab2:
    st.subheader("Cross-Reference Analysis")
    st.markdown("Find related concepts and references across all documents in your library.")
    
    # Topic or concept input
    search_concept = st.text_input(
        "🔎 Enter a topic or concept to find across documents",
        placeholder="e.g., machine learning, neural networks, quantum physics",
        help="Enter a topic to find related content across all your documents"
    )
    
    if search_concept and st.button("🔗 Find Cross-References", type="primary"):
        with st.spinner("Searching across documents..."):
            references = []
            
            # Search through all documents
            for doc in st.session_state.documents:
                prompt = f"""
                Analyze if the following document discusses or relates to the concept: "{search_concept}"
                
                Document: {doc['title']}
                Content: {doc['content'][:1500]}...
                
                If relevant, provide:
                1. How this document relates to "{search_concept}" (1-2 sentences)
                2. Key relevant quotes or sections
                3. Relevance score (0-10)
                
                Return JSON format:
                {{
                    "is_relevant": true/false,
                    "relevance_score": 0-10,
                    "relationship": "description",
                    "key_points": ["point1", "point2"]
                }}
                """
                
                try:
                    from google.genai import types
                    response = orchestrator.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    
                    if response.text:
                        import json
                        result = json.loads(response.text)
                        
                        if result.get('is_relevant') and result.get('relevance_score', 0) > 3:
                            references.append({
                                'document': doc,
                                'score': result.get('relevance_score', 0),
                                'relationship': result.get('relationship', ''),
                                'key_points': result.get('key_points', [])
                            })
                except:
                    continue
            
            # Display results
            if references:
                # Sort by relevance score
                references.sort(key=lambda x: x['score'], reverse=True)
                
                st.success(f"Found {len(references)} documents related to '{search_concept}'")
                
                # Export data
                export_text = f"# Cross-Reference Analysis\n\n"
                export_text += f"**Concept:** {search_concept}\n"
                export_text += f"**Documents Found:** {len(references)}\n\n"
                export_text += "---\n\n"
                
                for ref in references:
                    with st.expander(f"📄 {ref['document']['title']} (Relevance: {ref['score']}/10)"):
                        st.metric("Relevance Score", f"{ref['score']}/10")
                        st.markdown(f"**Relationship:** {ref['relationship']}")
                        
                        if ref['key_points']:
                            st.markdown("**Key Points:**")
                            for point in ref['key_points']:
                                st.markdown(f"- {point}")
                        
                        if st.button(f"📖 View Document", key=f"view_{ref['document']['id']}"):
                            st.session_state.selected_doc_for_summary = ref['document']['id']
                            st.switch_page("pages/1_📚_Document_Library.py")
                    
                    # Add to export
                    export_text += f"## {ref['document']['title']}\n"
                    export_text += f"**Relevance:** {ref['score']}/10\n"
                    export_text += f"**Relationship:** {ref['relationship']}\n"
                    export_text += "**Key Points:**\n"
                    for point in ref['key_points']:
                        export_text += f"- {point}\n"
                    export_text += "\n"
                
                # Download button
                st.download_button(
                    "💾 Download Cross-Reference Report",
                    data=export_text,
                    file_name=f"cross_reference_{search_concept.replace(' ', '_')}.md",
                    mime="text/markdown"
                )
            else:
                st.info(f"No significant references found for '{search_concept}' in your documents.")

# Sidebar tips
with st.sidebar:
    st.markdown("### 💡 Document Tools Tips")
    st.markdown("""
    **Document Comparison:**
    - Compare research papers to find contradictions
    - Analyze different perspectives on same topic
    - Synthesize information from multiple sources
    
    **Cross-References:**
    - Find all mentions of a specific concept
    - Track how ideas connect across documents
    - Build knowledge maps from your library
    
    **Best Practices:**
    - Use specific concepts for cross-referencing
    - Compare documents with related topics
    - Export results for further analysis
    """)
