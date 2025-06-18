import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import List, Dict, Any, Optional

Base = declarative_base()

class FlashcardSet(Base):
    __tablename__ = 'flashcard_sets'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(100), nullable=False)
    difficulty = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to flashcards
    flashcards = relationship("Flashcard", back_populates="flashcard_set", cascade="all, delete-orphan")

class Flashcard(Base):
    __tablename__ = 'flashcards'
    
    id = Column(Integer, primary_key=True, index=True)
    set_id = Column(Integer, ForeignKey('flashcard_sets.id'), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    difficulty = Column(String(50))
    topic = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to flashcard set
    flashcard_set = relationship("FlashcardSet", back_populates="flashcards")

class DatabaseManager:
    def __init__(self):
        """Initialize database connection and create tables"""
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not found")
        
        self.engine = create_engine(self.database_url)
        Base.metadata.create_all(bind=self.engine)
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.session = SessionLocal()
    
    def create_flashcard_set(self, title: str, subject: str, difficulty: str) -> int:
        """Create a new flashcard set and return its ID"""
        flashcard_set = FlashcardSet(
            title=title,
            subject=subject,
            difficulty=difficulty
        )
        self.session.add(flashcard_set)
        self.session.commit()
        self.session.refresh(flashcard_set)
        return int(flashcard_set.id)
    
    def add_flashcards_to_set(self, set_id: int, flashcards: List[Dict[str, Any]]) -> None:
        """Add multiple flashcards to a set"""
        for card_data in flashcards:
            flashcard = Flashcard(
                set_id=set_id,
                question=card_data.get('question', ''),
                answer=card_data.get('answer', ''),
                difficulty=card_data.get('difficulty', 'Medium'),
                topic=card_data.get('topic', '')
            )
            self.session.add(flashcard)
        self.session.commit()
    
    def get_all_flashcard_sets(self) -> List[Dict[str, Any]]:
        """Get all flashcard sets with basic info"""
        sets = self.session.query(FlashcardSet).order_by(FlashcardSet.created_at.desc()).all()
        return [
            {
                'id': fs.id,
                'title': fs.title,
                'subject': fs.subject,
                'difficulty': fs.difficulty,
                'created_at': fs.created_at,
                'card_count': len(fs.flashcards)
            }
            for fs in sets
        ]
    
    def get_flashcard_set_with_cards(self, set_id: int) -> Optional[Dict[str, Any]]:
        """Get a flashcard set with all its cards"""
        flashcard_set = self.session.query(FlashcardSet).filter(FlashcardSet.id == set_id).first()
        if not flashcard_set:
            return None
        
        return {
            'id': flashcard_set.id,
            'title': flashcard_set.title,
            'subject': flashcard_set.subject,
            'difficulty': flashcard_set.difficulty,
            'created_at': flashcard_set.created_at,
            'flashcards': [
                {
                    'id': card.id,
                    'question': card.question,
                    'answer': card.answer,
                    'difficulty': card.difficulty,
                    'topic': card.topic
                }
                for card in flashcard_set.flashcards
            ]
        }
    
    def update_flashcard(self, flashcard_id: int, question: str, answer: str) -> bool:
        """Update a flashcard's question and answer"""
        flashcard = self.session.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if flashcard:
            flashcard.question = question
            flashcard.answer = answer
            self.session.commit()
            return True
        return False
    
    def delete_flashcard_set(self, set_id: int) -> bool:
        """Delete a flashcard set and all its cards"""
        flashcard_set = self.session.query(FlashcardSet).filter(FlashcardSet.id == set_id).first()
        if flashcard_set:
            self.session.delete(flashcard_set)
            self.session.commit()
            return True
        return False
    
    def delete_flashcard(self, flashcard_id: int) -> bool:
        """Delete a single flashcard"""
        flashcard = self.session.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if flashcard:
            self.session.delete(flashcard)
            self.session.commit()
            return True
        return False
    
    def search_flashcard_sets(self, query: str) -> List[Dict[str, Any]]:
        """Search flashcard sets by title or subject"""
        sets = self.session.query(FlashcardSet).filter(
            (FlashcardSet.title.ilike(f'%{query}%')) |
            (FlashcardSet.subject.ilike(f'%{query}%'))
        ).order_by(FlashcardSet.created_at.desc()).all()
        
        return [
            {
                'id': fs.id,
                'title': fs.title,
                'subject': fs.subject,
                'difficulty': fs.difficulty,
                'created_at': fs.created_at,
                'card_count': len(fs.flashcards)
            }
            for fs in sets
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        total_sets = self.session.query(FlashcardSet).count()
        total_cards = self.session.query(Flashcard).count()
        
        subjects = self.session.query(FlashcardSet.subject).distinct().all()
        subject_list = [s[0] for s in subjects]
        
        return {
            'total_sets': total_sets,
            'total_cards': total_cards,
            'subjects': subject_list
        }
    
    def close(self):
        """Close database session"""
        self.session.close()
