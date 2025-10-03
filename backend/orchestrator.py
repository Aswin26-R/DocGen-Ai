import json
import logging
import os
from typing import List, Dict, Any
from google import genai
from google.genai import types
import streamlit as st

class AIOrchestrator:
    """LangChain-style orchestrator for AI-powered learning content generation"""
    
    def __init__(self):
        api_key = st.session_state.get('gemini_api_key') or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("Gemini API key not found in session or environment")
        self.client = genai.Client(api_key=api_key)
        
    def generate_summary(self, text: str, title: str = "") -> str:
        """Generate a comprehensive markdown-formatted summary"""
        prompt = f"""
        Please create a comprehensive markdown-formatted summary of the following document.
        
        Document Title: {title}
        
        Requirements:
        - Use proper markdown formatting with headers, bullet points, and emphasis
        - Include key concepts, main ideas, and important details
        - Structure the summary logically with clear sections
        - Keep it concise but comprehensive
        - Use bullet points for lists and key points
        
        Document Content:
        {text}
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text or "Failed to generate summary"
        except Exception as e:
            logging.error(f"Summary generation failed: {e}")
            return f"Error generating summary: {str(e)}"
    
    def generate_mcq_quiz(self, text: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """Generate multiple choice quiz questions from text"""
        prompt = f"""
        Generate {num_questions} multiple choice questions based on the following text.
        
        Requirements:
        - Each question should test understanding of key concepts
        - Provide 4 options (A, B, C, D) for each question
        - Include the correct answer and explanation
        - Questions should be challenging but fair
        - Include page/section references where possible
        
        Return the response as a JSON array with this structure:
        [
            {{
                "question": "Question text here?",
                "options": {{
                    "A": "Option A text",
                    "B": "Option B text", 
                    "C": "Option C text",
                    "D": "Option D text"
                }},
                "correct_answer": "A",
                "explanation": "Detailed explanation of why A is correct",
                "reference": "Section or page reference if available"
            }}
        ]
        
        Text content:
        {text}
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if response.text:
                questions = json.loads(response.text)
                return questions
            else:
                return []
        except Exception as e:
            logging.error(f"MCQ generation failed: {e}")
            return [{"error": f"Failed to generate quiz: {str(e)}"}]
    
    def generate_completion_exercise(self, text: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """Generate sentence completion exercises"""
        prompt = f"""
        Generate {num_questions} sentence completion exercises based on the following text.
        
        Requirements:
        - Create sentences with key terms or concepts removed
        - The missing part should be a single word or short phrase
        - Include the correct answer and explanation
        - Focus on important concepts and terminology
        
        Return as JSON array:
        [
            {{
                "sentence": "The process of _____ is essential for...",
                "correct_answer": "photosynthesis",
                "explanation": "Explanation of the concept",
                "hint": "Optional hint for the user"
            }}
        ]
        
        Text content:
        {text}
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if response.text:
                exercises = json.loads(response.text)
                return exercises
            else:
                return []
        except Exception as e:
            logging.error(f"Completion exercise generation failed: {e}")
            return [{"error": f"Failed to generate exercises: {str(e)}"}]
    
    def evaluate_answer(self, question: str, correct_answer: str, user_answer: str) -> Dict[str, Any]:
        """Evaluate user answer using semantic similarity"""
        prompt = f"""
        Evaluate the similarity between the correct answer and the user's answer.
        
        Question: {question}
        Correct Answer: {correct_answer}
        User Answer: {user_answer}
        
        Provide:
        1. A similarity score from 0-100
        2. Feedback explaining the evaluation
        3. Whether the answer should be considered correct (threshold: 70%)
        
        Return as JSON:
        {{
            "score": 85,
            "is_correct": true,
            "feedback": "Detailed feedback explaining the evaluation"
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if response.text:
                evaluation = json.loads(response.text)
                return evaluation
            else:
                return {"score": 0, "is_correct": False, "feedback": "Evaluation failed"}
        except Exception as e:
            logging.error(f"Answer evaluation failed: {e}")
            return {"score": 0, "is_correct": False, "feedback": f"Error: {str(e)}"}
    
    def extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts and terms from text"""
        prompt = f"""
        Extract the main concepts, key terms, and important ideas from the following text.
        Return as a JSON array of strings, with each concept being a word or short phrase.
        Focus on the most important 10-15 concepts.
        
        Text:
        {text}
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if response.text:
                concepts = json.loads(response.text)
                return concepts if isinstance(concepts, list) else []
            else:
                return []
        except Exception as e:
            logging.error(f"Concept extraction failed: {e}")
            return []
