import streamlit as st
from backend.auth import check_authentication, render_logout_button
from backend.utils import initialize_session_state, log_activity, get_document_by_id
from backend.orchestrator import AIOrchestrator
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="Quiz Center - DocGen",
    page_icon="🧠",
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

st.title("🧠 Quiz Center")
st.markdown("Generate and take AI-powered quizzes from your documents.")

# Check if a document was selected for quiz
selected_doc_id = st.session_state.get('selected_doc_for_quiz')

if not st.session_state.documents:
    st.warning("No documents in your library. Please upload documents first.")
    if st.button("📚 Go to Document Library"):
        st.switch_page("pages/1_📚_Document_Library.py")
    st.stop()

# Tabs for different quiz modes
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Multiple Choice", "✍️ Sentence Completion", "💬 Q&A Exercise", "📈 Quiz History"])

with tab1:
    st.subheader("Multiple Choice Quiz")
    
    # Document selection
    doc_options = {doc['title']: doc['id'] for doc in st.session_state.documents}
    selected_title = st.selectbox(
        "Select Document",
        options=list(doc_options.keys()),
        index=list(doc_options.values()).index(selected_doc_id) if selected_doc_id in doc_options.values() else 0
    )
    selected_doc = get_document_by_id(doc_options[selected_title])
    
    # Quiz settings
    col1, col2 = st.columns(2)
    with col1:
        num_questions = st.slider("Number of questions", 3, 10, 5)
    with col2:
        difficulty = st.select_slider("Difficulty", ["Easy", "Medium", "Hard"], "Medium")
    
    # Generate quiz
    if st.button("🎲 Generate Quiz", type="primary"):
        with st.spinner("Generating quiz questions..."):
            quiz_data = orchestrator.generate_mcq_quiz(
                selected_doc['content'],
                num_questions=num_questions
            )
        
        if quiz_data and 'error' not in quiz_data[0]:
            st.session_state.current_quiz = {
                'type': 'multiple_choice',
                'document_id': selected_doc['id'],
                'document_title': selected_doc['title'],
                'questions': quiz_data,
                'answers': {},
                'started_at': datetime.now().isoformat(),
                'difficulty': difficulty
            }
            st.success("Quiz generated! Answer the questions below.")
        else:
            st.error("Failed to generate quiz. Please try again.")
    
    # Display current quiz
    if st.session_state.current_quiz and st.session_state.current_quiz['type'] == 'multiple_choice':
        quiz = st.session_state.current_quiz
        st.markdown("---")
        st.subheader(f"Quiz: {quiz['document_title']}")
        
        all_answered = True
        
        for i, question in enumerate(quiz['questions']):
            st.markdown(f"**Question {i+1}:** {question['question']}")
            
            answer = st.radio(
                "Choose your answer:",
                options=list(question['options'].keys()),
                format_func=lambda x: f"{x}: {question['options'][x]}",
                key=f"mcq_{i}",
                index=None
            )
            
            if answer:
                quiz['answers'][i] = answer
            else:
                all_answered = False
            
            st.markdown("---")
        
        # Submit quiz
        if all_answered:
            if st.button("✅ Submit Quiz", type="primary"):
                # Calculate score
                correct_count = 0
                total_questions = len(quiz['questions'])
                
                for i, question in enumerate(quiz['questions']):
                    if quiz['answers'].get(i) == question['correct_answer']:
                        correct_count += 1
                
                score = (correct_count / total_questions) * 100
                
                # Show results
                st.success(f"Quiz completed! Score: {score:.1f}% ({correct_count}/{total_questions})")
                
                # Show detailed feedback
                st.subheader("📋 Detailed Results")
                for i, question in enumerate(quiz['questions']):
                    user_answer = quiz['answers'].get(i)
                    is_correct = user_answer == question['correct_answer']
                    
                    status_icon = "✅" if is_correct else "❌"
                    st.markdown(f"{status_icon} **Question {i+1}:** {question['question']}")
                    
                    if not is_correct:
                        st.markdown(f"Your answer: **{user_answer}** - {question['options'][user_answer]}")
                        st.markdown(f"Correct answer: **{question['correct_answer']}** - {question['options'][question['correct_answer']]}")
                    
                    st.markdown(f"*Explanation:* {question['explanation']}")
                    
                    if question.get('reference'):
                        st.markdown(f"*Reference:* {question['reference']}")
                    
                    st.markdown("---")
                
                # Save to history
                quiz_result = {
                    'id': f"quiz_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'type': 'multiple_choice',
                    'document_id': quiz['document_id'],
                    'document_title': quiz['document_title'],
                    'score': score,
                    'total_questions': total_questions,
                    'correct_answers': correct_count,
                    'completed_at': datetime.now().isoformat(),
                    'difficulty': quiz.get('difficulty', 'Medium'),
                    'time_taken': 'Not tracked'  # Could implement timer
                }
                st.session_state.quiz_history.append(quiz_result)
                log_activity(f"Completed MCQ quiz on {quiz['document_title']} - Score: {score:.1f}%")
                
                # Clear current quiz
                st.session_state.current_quiz = None
                
                st.balloons()

with tab2:
    st.subheader("Sentence Completion Exercise")
    
    # Document selection
    doc_options = {doc['title']: doc['id'] for doc in st.session_state.documents}
    selected_title = st.selectbox(
        "Select Document",
        options=list(doc_options.keys()),
        key="completion_doc"
    )
    selected_doc = get_document_by_id(doc_options[selected_title])
    
    # Settings
    num_exercises = st.slider("Number of exercises", 3, 10, 5, key="completion_num")
    
    # Generate exercises
    if st.button("🎯 Generate Exercises", type="primary"):
        with st.spinner("Generating completion exercises..."):
            exercises = orchestrator.generate_completion_exercise(
                selected_doc['content'],
                num_questions=num_exercises
            )
        
        if exercises and 'error' not in exercises[0]:
            st.session_state.current_completion = {
                'document_id': selected_doc['id'],
                'document_title': selected_doc['title'],
                'exercises': exercises,
                'answers': {},
                'started_at': datetime.now().isoformat()
            }
            st.success("Exercises generated!")
        else:
            st.error("Failed to generate exercises. Please try again.")
    
    # Display exercises
    if st.session_state.get('current_completion'):
        completion = st.session_state.current_completion
        st.markdown("---")
        st.subheader(f"Completion Exercise: {completion['document_title']}")
        
        for i, exercise in enumerate(completion['exercises']):
            st.markdown(f"**Exercise {i+1}:**")
            st.markdown(f"{exercise['sentence']}")
            
            if exercise.get('hint'):
                with st.expander("💡 Hint"):
                    st.info(exercise['hint'])
            
            answer = st.text_input(
                "Your answer:",
                key=f"completion_{i}",
                placeholder="Type your answer here..."
            )
            
            if answer:
                completion['answers'][i] = answer
            
            st.markdown("---")
        
        # Submit exercises
        if len(completion['answers']) == len(completion['exercises']):
            if st.button("✅ Submit Exercises", type="primary"):
                # Evaluate answers
                results = []
                total_score = 0
                
                for i, exercise in enumerate(completion['exercises']):
                    user_answer = completion['answers'].get(i, "")
                    evaluation = orchestrator.evaluate_answer(
                        f"Complete: {exercise['sentence']}",
                        exercise['correct_answer'],
                        user_answer
                    )
                    results.append(evaluation)
                    total_score += evaluation['score']
                
                avg_score = total_score / len(completion['exercises'])
                
                # Show results
                st.success(f"Exercises completed! Average Score: {avg_score:.1f}%")
                
                st.subheader("📋 Detailed Feedback")
                for i, (exercise, result) in enumerate(zip(completion['exercises'], results)):
                    status_icon = "✅" if result['is_correct'] else "❌"
                    st.markdown(f"{status_icon} **Exercise {i+1}:** Score: {result['score']:.1f}%")
                    st.markdown(f"Sentence: {exercise['sentence']}")
                    st.markdown(f"Your answer: **{completion['answers'][i]}**")
                    st.markdown(f"Expected answer: **{exercise['correct_answer']}**")
                    st.markdown(f"Feedback: {result['feedback']}")
                    st.markdown("---")
                
                # Save to history
                quiz_result = {
                    'id': f"completion_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'type': 'sentence_completion',
                    'document_id': completion['document_id'],
                    'document_title': completion['document_title'],
                    'score': avg_score,
                    'total_questions': len(completion['exercises']),
                    'completed_at': datetime.now().isoformat()
                }
                st.session_state.quiz_history.append(quiz_result)
                log_activity(f"Completed sentence completion on {completion['document_title']} - Score: {avg_score:.1f}%")
                
                # Clear current exercise
                st.session_state.current_completion = None

with tab3:
    st.subheader("Q&A Exercise")
    st.markdown("Generate questions and evaluate your understanding")
    
    # Document selection
    doc_options = {doc['title']: doc['id'] for doc in st.session_state.documents}
    selected_title = st.selectbox(
        "Select Document",
        options=list(doc_options.keys()),
        key="qa_doc"
    )
    selected_doc = get_document_by_id(doc_options[selected_title])
    
    st.markdown("**Ask a question about the document:**")
    user_question = st.text_area(
        "Your Question:",
        placeholder="What are the main concepts discussed in this document?",
        height=100
    )
    
    if user_question and st.button("📝 Generate Answer & Evaluate", type="primary"):
        with st.spinner("Generating reference answer..."):
            # Generate reference answer
            reference_prompt = f"""
            Based on the following document, provide a comprehensive answer to this question: {user_question}
            
            Document content:
            {selected_doc['content'][:3000]}...
            
            Provide a detailed, accurate answer based only on the document content.
            """
            
            try:
                response = orchestrator.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=reference_prompt
                )
                reference_answer = response.text
                
                st.subheader("📖 Reference Answer")
                st.markdown(reference_answer)
                
                st.subheader("✍️ Your Turn")
                user_answer = st.text_area(
                    "Provide your answer to the question:",
                    height=150,
                    placeholder="Write your answer here..."
                )
                
                if user_answer and st.button("🔍 Evaluate My Answer"):
                    with st.spinner("Evaluating your answer..."):
                        evaluation = orchestrator.evaluate_answer(
                            user_question,
                            reference_answer,
                            user_answer
                        )
                    
                    # Show evaluation
                    score_color = "green" if evaluation['score'] >= 70 else "orange" if evaluation['score'] >= 50 else "red"
                    
                    st.markdown(f"### 📊 Evaluation Result")
                    st.markdown(f"**Score:** :{score_color}[{evaluation['score']:.1f}%]")
                    st.markdown(f"**Status:** {'✅ Correct' if evaluation['is_correct'] else '❌ Needs Improvement'}")
                    
                    st.markdown("**Feedback:**")
                    st.info(evaluation['feedback'])
                    
                    # Save to history
                    qa_result = {
                        'id': f"qa_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        'type': 'qa_exercise',
                        'document_id': selected_doc['id'],
                        'document_title': selected_doc['title'],
                        'question': user_question,
                        'user_answer': user_answer,
                        'reference_answer': reference_answer,
                        'score': evaluation['score'],
                        'completed_at': datetime.now().isoformat()
                    }
                    st.session_state.quiz_history.append(qa_result)
                    log_activity(f"Completed Q&A exercise on {selected_doc['title']} - Score: {evaluation['score']:.1f}%")
                
            except Exception as e:
                st.error(f"Error generating reference answer: {e}")

with tab4:
    st.subheader("📈 Quiz History")
    
    if not st.session_state.quiz_history:
        st.info("No quiz history yet. Complete some quizzes to see your progress!")
    else:
        # Summary stats
        total_quizzes = len(st.session_state.quiz_history)
        avg_score = sum(q.get('score', 0) for q in st.session_state.quiz_history) / total_quizzes
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Quizzes", total_quizzes)
        with col2:
            st.metric("Average Score", f"{avg_score:.1f}%")
        with col3:
            recent_score = st.session_state.quiz_history[-1].get('score', 0) if st.session_state.quiz_history else 0
            st.metric("Latest Score", f"{recent_score:.1f}%")
        
        st.markdown("---")
        
        # Quiz history table
        for quiz in reversed(st.session_state.quiz_history[-10:]):  # Show last 10
            quiz_type_icons = {
                'multiple_choice': '🎯',
                'sentence_completion': '✍️',
                'qa_exercise': '💬'
            }
            
            icon = quiz_type_icons.get(quiz['type'], '📝')
            
            with st.expander(f"{icon} {quiz['type'].replace('_', ' ').title()} - {quiz['document_title'][:50]}... - {quiz['score']:.1f}%"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Document:** {quiz['document_title']}")
                    st.markdown(f"**Type:** {quiz['type'].replace('_', ' ').title()}")
                    st.markdown(f"**Score:** {quiz['score']:.1f}%")
                
                with col2:
                    st.markdown(f"**Completed:** {quiz['completed_at'][:16]}")
                    if quiz.get('total_questions'):
                        st.markdown(f"**Questions:** {quiz.get('correct_answers', 0)}/{quiz['total_questions']}")
                    if quiz.get('difficulty'):
                        st.markdown(f"**Difficulty:** {quiz['difficulty']}")
