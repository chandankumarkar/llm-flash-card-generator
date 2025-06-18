import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
import json
import io
from flashcard_generator import FlashcardGenerator
from utils import extract_text_from_pdf, validate_file_type
from database import DatabaseManager

# Initialize the flashcard generator
@st.cache_resource
def get_flashcard_generator():
    return FlashcardGenerator()

# Initialize database manager
@st.cache_resource
def get_database_manager():
    return DatabaseManager()

def main():
    st.title("🎓 AI Flashcard Generator")
    st.markdown("Transform your educational content into interactive flashcards using AI")
    
    # Initialize session state
    if 'flashcards' not in st.session_state:
        st.session_state.flashcards = []
    if 'edited_flashcards' not in st.session_state:
        st.session_state.edited_flashcards = []
    if 'current_set_id' not in st.session_state:
        st.session_state.current_set_id = None
    
    generator = get_flashcard_generator()
    db = get_database_manager()
    
    # Create main tabs
    tab1, tab2, tab3 = st.tabs(["🚀 Generate", "📚 My Flashcards", "📊 Stats"])
    
    with tab1:
        generate_flashcards_tab(generator, db)
    
    with tab2:
        manage_flashcards_tab(db)
    
    with tab3:
        statistics_tab(db)

def generate_flashcards_tab(generator, db):
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Subject selection
        subject = st.selectbox(
            "Select Subject Type",
            ["General", "Biology", "Chemistry", "Physics", "History", "Literature", 
             "Mathematics", "Computer Science", "Psychology", "Economics"],
            help="Choose the subject to optimize flashcard generation"
        )
        
        # Number of flashcards
        num_flashcards = st.slider(
            "Number of Flashcards",
            min_value=5,
            max_value=25,
            value=15,
            help="Choose how many flashcards to generate"
        )
        
        # Difficulty level
        difficulty = st.selectbox(
            "Difficulty Level",
            ["Mixed", "Easy", "Medium", "Hard"],
            help="Set the difficulty level for generated questions"
        )
    
    # Main content area
    st.header("📝 Input Educational Content")
    
    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["📄 File Upload", "✏️ Direct Input"])
    
    # Initialize content in session state
    if 'content' not in st.session_state:
        st.session_state.content = ""
    
    with tab1:
        st.markdown("Upload your educational materials (.txt or .pdf files)")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['txt', 'pdf'],
            help="Upload text files or PDF documents containing educational content"
        )
        
        if uploaded_file is not None:
            if validate_file_type(uploaded_file):
                try:
                    if uploaded_file.type == "application/pdf":
                        st.session_state.content = extract_text_from_pdf(uploaded_file)
                        st.success(f"PDF processed successfully! Extracted {len(st.session_state.content)} characters.")
                    else:
                        st.session_state.content = str(uploaded_file.read(), "utf-8")
                        st.success(f"Text file loaded successfully! {len(st.session_state.content)} characters.")
                    
                    # Preview content
                    with st.expander("📖 Preview Content"):
                        preview_text = st.session_state.content[:1000] + "..." if len(st.session_state.content) > 1000 else st.session_state.content
                        st.text_area("Extracted Content", preview_text, height=200, disabled=True)
                        
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
            else:
                st.error("Please upload a valid .txt or .pdf file")
    
    with tab2:
        st.markdown("Paste your educational content directly")
        direct_content = st.text_area(
            "Educational Content",
            height=300,
            placeholder="Paste your lecture notes, textbook excerpts, or any educational material here...",
            help="Enter the educational content you want to convert into flashcards"
        )
        if direct_content:
            st.session_state.content = direct_content
    
    # Use the content from session state
    content = st.session_state.content
    
    # Show content status for debugging
    if content.strip():
        st.info(f"Content loaded: {len(content)} characters")
    
    # Generate flashcards button
    if st.button("🚀 Generate Flashcards", type="primary", disabled=not content.strip()):
        if len(content.strip()) < 50:
            st.warning("Please provide more content (at least 50 characters) for better flashcard generation.")
        else:
            generator = get_flashcard_generator()
            is_api_working, api_message = generator.test_api_connection()
            
            if not is_api_working:
                st.warning(f"API Issue: {api_message}")
                st.info("Running in demo mode - generating sample flashcards for testing")
                use_demo_mode = True
            else:
                use_demo_mode = False
            
            spinner_text = "Generating demo flashcards..." if use_demo_mode else "Generating flashcards with AI..."
            with st.spinner(spinner_text):
                try:
                    if use_demo_mode:
                        flashcards = generator.generate_demo_flashcards(
                            content=content,
                            subject=subject,
                            num_flashcards=num_flashcards,
                            difficulty=difficulty
                        )
                    else:
                        flashcards = generator.generate_flashcards(
                            content=content,
                            subject=subject,
                            num_flashcards=num_flashcards,
                            difficulty=difficulty
                        )
                    
                    if flashcards:
                        st.session_state.flashcards = flashcards
                        st.session_state.edited_flashcards = flashcards.copy()
                        success_message = f"Successfully generated {len(flashcards)} flashcards!"
                        if use_demo_mode:
                            success_message += " (Demo Mode)"
                        st.success(success_message)
                    else:
                        st.error("Failed to generate flashcards. Please try again.")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "invalid_api_key" in error_msg or "401" in error_msg:
                        st.error("❌ Invalid OpenAI API key. Please check your API key.")
                    elif "insufficient_quota" in error_msg:
                        st.error("❌ OpenAI quota exceeded. Please check your account billing.")
                    else:
                        st.error(f"❌ Error generating flashcards: {error_msg}")
    
    # Display and edit flashcards
    if st.session_state.flashcards:
        st.header("📚 Generated Flashcards")
        st.markdown(f"**Total:** {len(st.session_state.flashcards)} flashcards")
        
        # Review and edit mode
        edit_mode = st.checkbox("✏️ Enable Edit Mode", help="Turn on to edit questions and answers")
        
        for i, flashcard in enumerate(st.session_state.flashcards):
            with st.expander(f"Card {i+1}: {flashcard['question'][:50]}{'...' if len(flashcard['question']) > 50 else ''}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Question:**")
                    if edit_mode:
                        edited_question = st.text_area(
                            f"Edit Question {i+1}",
                            value=flashcard['question'],
                            key=f"q_{i}",
                            height=100
                        )
                        st.session_state.edited_flashcards[i]['question'] = edited_question
                    else:
                        st.write(flashcard['question'])
                
                with col2:
                    st.markdown("**Answer:**")
                    if edit_mode:
                        edited_answer = st.text_area(
                            f"Edit Answer {i+1}",
                            value=flashcard['answer'],
                            key=f"a_{i}",
                            height=100
                        )
                        st.session_state.edited_flashcards[i]['answer'] = edited_answer
                    else:
                        st.write(flashcard['answer'])
                
                # Show additional metadata if available
                if 'difficulty' in flashcard:
                    st.caption(f"🎯 Difficulty: {flashcard['difficulty']}")
                if 'topic' in flashcard:
                    st.caption(f"📂 Topic: {flashcard['topic']}")
        
        # Save to database option
        st.header("💾 Save & Export Flashcards")
        
        # Save to database
        col1, col2 = st.columns([2, 1])
        with col1:
            save_title = st.text_input("Set Title:", value=f"{subject} - {len(st.session_state.flashcards)} cards", key="save_title")
        with col2:
            st.write("")
            st.write("")
            if st.button("💾 Save to Database", key="save_db"):
                if save_title.strip():
                    try:
                        db = get_database_manager()
                        set_id = db.create_flashcard_set(save_title.strip(), subject, difficulty)
                        db.add_flashcards_to_set(set_id, st.session_state.edited_flashcards)
                        st.success(f"Saved flashcard set: {save_title}")
                        st.session_state.current_set_id = set_id
                    except Exception as e:
                        st.error(f"Error saving to database: {str(e)}")
                else:
                    st.warning("Please enter a title for the flashcard set")
        
        st.subheader("Export Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Export as CSV"):
                csv_data = generate_csv_export(st.session_state.edited_flashcards)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_data,
                    file_name="flashcards.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📋 Export as JSON"):
                json_data = generate_json_export(st.session_state.edited_flashcards)
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_data,
                    file_name="flashcards.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button("🃏 Export for Anki"):
                anki_data = generate_anki_export(st.session_state.edited_flashcards)
                st.download_button(
                    label="⬇️ Download Anki Format",
                    data=anki_data,
                    file_name="flashcards_anki.txt",
                    mime="text/plain"
                )
        
        # Clear flashcards button
        if st.button("🗑️ Clear All Flashcards"):
            st.session_state.flashcards = []
            st.session_state.edited_flashcards = []
            st.rerun()

def manage_flashcards_tab(db):
    """Tab for managing saved flashcard sets"""
    st.header("📚 My Saved Flashcard Sets")
    
    # Search functionality
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("🔍 Search flashcard sets", placeholder="Search by title or subject...")
    with col2:
        st.write("")
        st.write("")
        if st.button("🔍 Search"):
            st.rerun()
    
    try:
        # Get flashcard sets (search or all)
        if search_query:
            flashcard_sets = db.search_flashcard_sets(search_query)
        else:
            flashcard_sets = db.get_all_flashcard_sets()
        
        if not flashcard_sets:
            if search_query:
                st.info("No flashcard sets found matching your search.")
            else:
                st.info("No saved flashcard sets yet. Generate some flashcards first!")
            return
        
        # Display flashcard sets
        for fs in flashcard_sets:
            with st.expander(f"📚 {fs['title']} ({fs['card_count']} cards)"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Subject:** {fs['subject']}")
                    st.write(f"**Difficulty:** {fs['difficulty']}")
                    st.write(f"**Created:** {fs['created_at'].strftime('%Y-%m-%d %H:%M')}")
                
                with col2:
                    if st.button(f"👁️ View", key=f"view_{fs['id']}"):
                        view_flashcard_set(db, fs['id'])
                
                with col3:
                    if st.button(f"🗑️ Delete", key=f"delete_{fs['id']}"):
                        if db.delete_flashcard_set(fs['id']):
                            st.success("Deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete set")
    
    except Exception as e:
        st.error(f"Error loading flashcard sets: {str(e)}")

def view_flashcard_set(db, set_id):
    """Display a specific flashcard set"""
    try:
        flashcard_data = db.get_flashcard_set_with_cards(set_id)
        if not flashcard_data:
            st.error("Flashcard set not found")
            return
        
        st.subheader(f"📚 {flashcard_data['title']}")
        st.write(f"**Subject:** {flashcard_data['subject']} | **Difficulty:** {flashcard_data['difficulty']}")
        st.write(f"**Cards:** {len(flashcard_data['flashcards'])}")
        
        # Display flashcards
        for i, card in enumerate(flashcard_data['flashcards']):
            with st.expander(f"Card {i+1}: {card['question'][:50]}{'...' if len(card['question']) > 50 else ''}"):
                st.write("**Question:**")
                st.write(card['question'])
                st.write("**Answer:**")
                st.write(card['answer'])
                if card['topic']:
                    st.caption(f"Topic: {card['topic']}")
                if card['difficulty']:
                    st.caption(f"Difficulty: {card['difficulty']}")
        
        # Export options for this set
        st.subheader("💾 Export Options")
        col1, col2, col3 = st.columns(3)
        
        flashcards_list = flashcard_data['flashcards']
        
        with col1:
            if st.button("📄 Export CSV", key=f"csv_{set_id}"):
                csv_data = generate_csv_export(flashcards_list)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_data,
                    file_name=f"{flashcard_data['title']}_flashcards.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📋 Export JSON", key=f"json_{set_id}"):
                json_data = generate_json_export(flashcards_list)
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_data,
                    file_name=f"{flashcard_data['title']}_flashcards.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button("🃏 Export Anki", key=f"anki_{set_id}"):
                anki_data = generate_anki_export(flashcards_list)
                st.download_button(
                    label="⬇️ Download Anki",
                    data=anki_data,
                    file_name=f"{flashcard_data['title']}_anki.txt",
                    mime="text/plain"
                )
    
    except Exception as e:
        st.error(f"Error viewing flashcard set: {str(e)}")

def statistics_tab(db):
    """Tab showing database statistics"""
    st.header("📊 Statistics")
    
    try:
        stats = db.get_statistics()
        
        # Display key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Sets", stats['total_sets'])
        
        with col2:
            st.metric("Total Cards", stats['total_cards'])
        
        with col3:
            avg_cards = stats['total_cards'] / max(stats['total_sets'], 1)
            st.metric("Avg Cards/Set", f"{avg_cards:.1f}")
        
        # Subject breakdown
        if stats['subjects']:
            st.subheader("📚 Subjects")
            for subject in stats['subjects']:
                st.write(f"• {subject}")
        
        # Recent activity could be added here
        st.subheader("🔄 Database Status")
        st.success("✅ Database connection active")
        
    except Exception as e:
        st.error(f"Error loading statistics: {str(e)}")
        st.info("Database may not be properly initialized")

def generate_csv_export(flashcards):
    """Generate CSV format for flashcards export"""
    df = pd.DataFrame(flashcards)
    return df.to_csv(index=False)

def generate_json_export(flashcards):
    """Generate JSON format for flashcards export"""
    export_data = {
        "flashcards": flashcards,
        "total_count": len(flashcards),
        "exported_at": pd.Timestamp.now().isoformat()
    }
    return json.dumps(export_data, indent=2)

def generate_anki_export(flashcards):
    """Generate Anki-compatible format for flashcards export"""
    anki_content = []
    for card in flashcards:
        # Anki format: Question<tab>Answer
        line = f"{card['question']}\t{card['answer']}"
        anki_content.append(line)
    return "\n".join(anki_content)

if __name__ == "__main__":
    main()

