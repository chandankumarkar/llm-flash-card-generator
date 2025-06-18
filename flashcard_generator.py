import os
import json
from typing import List, Dict, Any
from openai import OpenAI

class FlashcardGenerator:
    def __init__(self):
        """Initialize the flashcard generator with OpenAI client"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-4o"
    
    def test_api_connection(self) -> tuple[bool, str]:
        """Test if the OpenAI API key is working"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True, "API connection successful"
        except Exception as e:
            error_message = str(e)
            if "invalid_api_key" in error_message or "401" in error_message:
                return False, "Invalid or expired API key. Please check your OpenAI API key."
            elif "insufficient_quota" in error_message:
                return False, "API quota exceeded. Please check your OpenAI account billing."
            else:
                return False, f"API connection failed: {error_message}"
    
    def generate_demo_flashcards(self, content: str, subject: str = "General", 
                                num_flashcards: int = 15, difficulty: str = "Mixed") -> List[Dict[str, Any]]:
        """Generate demo flashcards for testing when API is not available"""
        demo_templates = {
            "Biology": [
                {"question": "What is photosynthesis?", "answer": "The process by which plants convert light energy into chemical energy using chlorophyll.", "difficulty": "Easy", "topic": "Plant Biology"},
                {"question": "What is the function of mitochondria?", "answer": "Mitochondria are the powerhouse of the cell, producing ATP through cellular respiration.", "difficulty": "Medium", "topic": "Cell Biology"},
                {"question": "What is DNA?", "answer": "Deoxyribonucleic acid, the hereditary material that contains genetic instructions for all living organisms.", "difficulty": "Medium", "topic": "Genetics"},
            ],
            "Chemistry": [
                {"question": "What is the periodic table?", "answer": "A tabular arrangement of chemical elements organized by atomic number and electron configuration.", "difficulty": "Easy", "topic": "Elements"},
                {"question": "What is a covalent bond?", "answer": "A chemical bond formed by the sharing of electrons between atoms.", "difficulty": "Medium", "topic": "Chemical Bonding"},
                {"question": "What is pH?", "answer": "A scale used to measure the acidity or alkalinity of a solution, ranging from 0 to 14.", "difficulty": "Medium", "topic": "Acids and Bases"},
            ],
            "Physics": [
                {"question": "What is Newton's first law?", "answer": "An object at rest stays at rest and an object in motion stays in motion unless acted upon by an external force.", "difficulty": "Medium", "topic": "Classical Mechanics"},
                {"question": "What is the speed of light?", "answer": "Approximately 299,792,458 meters per second in a vacuum.", "difficulty": "Easy", "topic": "Optics"},
                {"question": "What is energy?", "answer": "The capacity to do work or cause change, existing in various forms like kinetic, potential, and thermal.", "difficulty": "Easy", "topic": "Energy"},
            ],
            "General": [
                {"question": "What is the main topic of this content?", "answer": "Based on the provided educational material, this covers fundamental concepts in the subject area.", "difficulty": "Easy", "topic": "Overview"},
                {"question": "What are the key concepts mentioned?", "answer": "The content discusses important principles and definitions relevant to understanding the subject matter.", "difficulty": "Medium", "topic": "Key Concepts"},
                {"question": "How can this knowledge be applied?", "answer": "These concepts form the foundation for more advanced study and practical application in the field.", "difficulty": "Medium", "topic": "Application"},
            ]
        }
        
        # Get appropriate templates or use general ones
        templates = demo_templates.get(subject, demo_templates["General"])
        
        # Generate flashcards based on requested number
        flashcards = []
        for i in range(min(num_flashcards, len(templates) * 3)):  # Allow up to 3x templates
            template_index = i % len(templates)
            template = templates[template_index].copy()
            
            # Add some variation for repeated templates
            if i >= len(templates):
                variation = i // len(templates)
                template["question"] = f"[Variation {variation + 1}] {template['question']}"
                template["answer"] = f"{template['answer']} (Additional context based on provided content)"
            
            # Set difficulty based on request
            if difficulty != "Mixed":
                template["difficulty"] = difficulty
            
            flashcards.append(template)
        
        return flashcards[:num_flashcards]
    
    def generate_flashcards(self, content: str, subject: str = "General", 
                          num_flashcards: int = 15, difficulty: str = "Mixed") -> List[Dict[str, Any]]:
        """
        Generate flashcards from educational content using OpenAI GPT
        
        Args:
            content: Educational text content
            subject: Subject type for optimized prompting
            num_flashcards: Number of flashcards to generate
            difficulty: Difficulty level (Easy, Medium, Hard, Mixed)
        
        Returns:
            List of flashcard dictionaries with question, answer, and metadata
        """
        try:
            prompt = self._create_prompt(content, subject, num_flashcards, difficulty)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational content creator specializing in generating high-quality flashcards for learning and retention."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=3000
            )
            
            response_content = response.choices[0].message.content
            if response_content is None:
                raise ValueError("Empty response from OpenAI")
            result = json.loads(response_content)
            
            # Validate and process the response
            if "flashcards" in result and isinstance(result["flashcards"], list):
                flashcards = []
                for card in result["flashcards"]:
                    if self._validate_flashcard(card):
                        flashcards.append({
                            "question": card.get("question", "").strip(),
                            "answer": card.get("answer", "").strip(),
                            "difficulty": card.get("difficulty", difficulty),
                            "topic": card.get("topic", subject)
                        })
                
                return flashcards[:num_flashcards]  # Ensure we don't exceed requested number
            else:
                raise ValueError("Invalid response format from OpenAI")
                
        except Exception as e:
            print(f"Error generating flashcards: {str(e)}")
            raise e
    
    def _create_prompt(self, content: str, subject: str, num_flashcards: int, difficulty: str) -> str:
        """Create an optimized prompt for flashcard generation"""
        
        difficulty_instructions = {
            "Easy": "Focus on basic concepts, definitions, and simple recall questions.",
            "Medium": "Include application-based questions and moderate complexity concepts.",
            "Hard": "Create analytical, synthesis, and evaluation-level questions requiring deep understanding.",
            "Mixed": "Include a variety of difficulty levels from basic recall to analytical thinking."
        }
        
        subject_guidance = {
            "Biology": "Focus on biological processes, organisms, anatomy, and scientific principles.",
            "Chemistry": "Emphasize chemical reactions, formulas, periodic table, and laboratory concepts.",
            "Physics": "Concentrate on laws, formulas, phenomena, and problem-solving concepts.",
            "History": "Include dates, events, causes and effects, and historical significance.",
            "Literature": "Focus on themes, characters, literary devices, and analysis.",
            "Mathematics": "Include formulas, theorems, problem-solving steps, and mathematical concepts.",
            "Computer Science": "Emphasize algorithms, data structures, programming concepts, and technical definitions.",
            "Psychology": "Focus on theories, terminology, research methods, and psychological phenomena.",
            "Economics": "Include economic principles, theories, market concepts, and terminology.",
            "General": "Create well-rounded questions covering key concepts and important information."
        }
        
        prompt = f"""
You are tasked with creating {num_flashcards} high-quality educational flashcards from the provided content.

SUBJECT: {subject}
DIFFICULTY LEVEL: {difficulty}
INSTRUCTIONS: {difficulty_instructions.get(difficulty, difficulty_instructions["Mixed"])}
SUBJECT GUIDANCE: {subject_guidance.get(subject, subject_guidance["General"])}

CONTENT TO PROCESS:
{content}

REQUIREMENTS:
1. Generate exactly {num_flashcards} flashcards
2. Each flashcard must have a clear, specific question and a comprehensive answer
3. Questions should test understanding, not just memorization
4. Answers should be complete and self-contained (no references to "the text above")
5. Focus on the most important concepts and information
6. Ensure factual accuracy and educational value
7. Vary question types (definition, application, analysis, comparison, etc.)
8. If the content allows, distribute questions across different topics/sections

RESPONSE FORMAT:
Respond with a JSON object containing a "flashcards" array. Each flashcard should have:
- "question": A clear, specific question
- "answer": A comprehensive, accurate answer
- "difficulty": The difficulty level of this specific question
- "topic": The specific topic or concept this flashcard covers

Example format:
{{
  "flashcards": [
    {{
      "question": "What is photosynthesis and why is it important for life on Earth?",
      "answer": "Photosynthesis is the process by which plants convert light energy into chemical energy, producing glucose and oxygen from carbon dioxide and water. It's crucial because it provides oxygen for most life forms and forms the base of most food chains.",
      "difficulty": "Medium",
      "topic": "Plant Biology"
    }}
  ]
}}

Generate the flashcards now:
"""
        return prompt
    
    def _validate_flashcard(self, card: Dict) -> bool:
        """Validate that a flashcard has required fields and content"""
        required_fields = ["question", "answer"]
        
        for field in required_fields:
            if field not in card or not card[field] or len(card[field].strip()) < 10:
                return False
        
        # Additional validation
        if len(card["question"]) > 500 or len(card["answer"]) > 1000:
            return False
            
        return True
    
    def enhance_flashcard(self, question: str, answer: str, subject: str) -> Dict[str, str]:
        """Enhance a single flashcard with better formatting and additional context"""
        try:
            prompt = f"""
Improve the following flashcard for the subject '{subject}':

Question: {question}
Answer: {answer}

Please enhance this flashcard by:
1. Making the question more specific and clear
2. Improving the answer with better structure and completeness
3. Ensuring educational value and accuracy

Respond in JSON format:
{{
  "enhanced_question": "improved question here",
  "enhanced_answer": "improved answer here"
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational content editor focused on improving learning materials."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=500
            )
            
            enhance_content = response.choices[0].message.content
            if not enhance_content:
                raise ValueError("Empty response from OpenAI")
            result = json.loads(enhance_content)
            return {
                "question": result.get("enhanced_question", question),
                "answer": result.get("enhanced_answer", answer)
            }
            
        except Exception as e:
            print(f"Error enhancing flashcard: {str(e)}")
            return {"question": question, "answer": answer}

