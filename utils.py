import PyPDF2
import io
import streamlit as st
from typing import Optional

def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extract text content from an uploaded PDF file
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        Extracted text content as string
    """
    try:
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        
        # Extract text from all pages
        text_content = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text_content += page.extract_text() + "\n"
        
        if not text_content.strip():
            raise ValueError("No text could be extracted from the PDF. The file might be image-based or corrupted.")
        
        return text_content.strip()
        
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def validate_file_type(uploaded_file) -> bool:
    """
    Validate that the uploaded file is of an acceptable type
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        True if file type is valid, False otherwise
    """
    if uploaded_file is None:
        return False
    
    allowed_types = ['text/plain', 'application/pdf']
    return uploaded_file.type in allowed_types

def clean_text_content(text: str) -> str:
    """
    Clean and normalize text content for better processing
    
    Args:
        text: Raw text content
    
    Returns:
        Cleaned text content
    """
    if not text:
        return ""
    
    # Remove excessive whitespace and normalize line breaks
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:  # Only keep non-empty lines
            cleaned_lines.append(line)
    
    # Join lines with single spaces, but preserve paragraph breaks
    cleaned_text = ""
    for i, line in enumerate(cleaned_lines):
        cleaned_text += line
        # Add appropriate spacing
        if i < len(cleaned_lines) - 1:
            next_line = cleaned_lines[i + 1]
            # If the current line ends with punctuation and next line starts with capital
            # or if current line is short (likely a heading), add double space for paragraph break
            if (line.endswith('.') or line.endswith('!') or line.endswith('?') or len(line) < 50) and \
               next_line and next_line[0].isupper():
                cleaned_text += "\n\n"
            else:
                cleaned_text += " "
    
    return cleaned_text

def format_flashcard_for_export(flashcard: dict, format_type: str = "standard") -> dict:
    """
    Format a flashcard for different export types
    
    Args:
        flashcard: Dictionary containing flashcard data
        format_type: Type of formatting (standard, anki, quizlet)
    
    Returns:
        Formatted flashcard dictionary
    """
    formatted = flashcard.copy()
    
    if format_type == "anki":
        # Anki-specific formatting
        formatted['question'] = flashcard['question'].replace('\n', '<br>')
        formatted['answer'] = flashcard['answer'].replace('\n', '<br>')
    
    elif format_type == "quizlet":
        # Quizlet-specific formatting
        formatted['term'] = flashcard['question']
        formatted['definition'] = flashcard['answer']
    
    return formatted

def estimate_reading_time(text: str) -> int:
    """
    Estimate reading time for given text (in minutes)
    Average reading speed: 200 words per minute
    
    Args:
        text: Text content to analyze
    
    Returns:
        Estimated reading time in minutes
    """
    if not text:
        return 0
    
    word_count = len(text.split())
    reading_time = max(1, round(word_count / 200))  # Minimum 1 minute
    return reading_time

def get_content_stats(text: str) -> dict:
    """
    Get basic statistics about the text content
    
    Args:
        text: Text content to analyze
    
    Returns:
        Dictionary with content statistics
    """
    if not text:
        return {
            "character_count": 0,
            "word_count": 0,
            "paragraph_count": 0,
            "estimated_reading_time": 0
        }
    
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    words = text.split()
    
    return {
        "character_count": len(text),
        "word_count": len(words),
        "paragraph_count": len(paragraphs),
        "estimated_reading_time": estimate_reading_time(text)
    }

def validate_flashcard_content(question: str, answer: str) -> tuple[bool, str]:
    """
    Validate flashcard content for quality and completeness
    
    Args:
        question: Question text
        answer: Answer text
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not question or not question.strip():
        return False, "Question cannot be empty"
    
    if not answer or not answer.strip():
        return False, "Answer cannot be empty"
    
    if len(question.strip()) < 10:
        return False, "Question is too short (minimum 10 characters)"
    
    if len(answer.strip()) < 10:
        return False, "Answer is too short (minimum 10 characters)"
    
    if len(question) > 500:
        return False, "Question is too long (maximum 500 characters)"
    
    if len(answer) > 1000:
        return False, "Answer is too long (maximum 1000 characters)"
    
    return True, ""

