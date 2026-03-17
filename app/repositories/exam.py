from google.cloud.firestore import Client
from typing import List, Optional
from app.repositories.base import BaseRepository
from app.models.exam import Year, Subject, Topic, Question, Subquestion, Diagram, Figure
from app.schemas.exam import ExamPaperData

class ExamRepository:
    """
    Complex repository to handle the normalized saving of full Exam Paper Data
    across multiple disconnected collections in Firestore.
    """
    def __init__(self, db: Client):
        self.db = db
        self.year_repo = BaseRepository(db, Year, "years")
        self.subject_repo = BaseRepository(db, Subject, "subjects")
        self.topic_repo = BaseRepository(db, Topic, "topics")
        self.question_repo = BaseRepository(db, Question, "questions")
        self.subquestion_repo = BaseRepository(db, Subquestion, "subquestions")
        self.diagram_repo = BaseRepository(db, Diagram, "diagrams")
        self.figure_repo = BaseRepository(db, Figure, "figures")

    def _ensure_year_exists(self, year_num: int, subject_name: str) -> None:
        """Creates or updates a year document."""
        year_id = str(year_num)
        year_doc = self.year_repo.get(year_id)
        
        if not year_doc:
            self.year_repo.create(Year(year=year_num, name=[subject_name]), doc_id=year_id)
        else:
            if subject_name not in year_doc.name:
                updated_names = year_doc.name + [subject_name]
                self.year_repo.update(year_id, {"name": updated_names})

    def _ensure_subject_exists(self, subject_name: str, level: str) -> None:
        """Creates a subject document if it doesn't exist."""
        subject_id = subject_name.lower().replace(" ", "_")
        subject_doc = self.subject_repo.get(subject_id)
        
        if not subject_doc:
            self.subject_repo.create(Subject(name=subject_name, level=level), doc_id=subject_id)

    def _ensure_topic_exists(self, topic_name: str, subtopic_name: str) -> None:
        """Creates or updates a topic document."""
        topic_id = topic_name.lower().replace(" ", "_")
        topic_doc = self.topic_repo.get(topic_id)
        
        if not topic_doc:
            self.topic_repo.create(Topic(name=topic_name, subtopics=[subtopic_name]), doc_id=topic_id)
        else:
            if subtopic_name not in topic_doc.subtopics:
                updated_subtopics = topic_doc.subtopics + [subtopic_name]
                self.topic_repo.update(topic_id, {"subtopics": updated_subtopics})

    def save_full_exam(self, exam_data: ExamPaperData) -> dict:
        """
        Takes the highly structured Pydantic DTO from the AI
        and normalizes it into Firestore database tables.
        """
        # 1. Setup metadata tables
        self._ensure_year_exists(exam_data.year, exam_data.subject)
        self._ensure_subject_exists(exam_data.subject, exam_data.level)
        
        saved_questions = 0
        
        # 2. Iterate through and save questions
        for q_data in exam_data.questions:
            self._ensure_topic_exists(q_data.topic, q_data.subtopic)
            
            question_model = Question(
                subject=exam_data.subject,
                year=exam_data.year,
                paper=exam_data.paper,
                question_number=q_data.question_number,
                has_subquestions=q_data.has_subquestions or len(q_data.subquestions) > 0,
                question_text=q_data.question_text,
                topic=q_data.topic,
                subtopic=q_data.subtopic,
                marks_total=q_data.marks_total,
                question_type=q_data.question_type,
                has_diagram=q_data.has_diagram,
                has_figure=q_data.has_figure
            )
            
            # Save parent question to get its ID
            saved_q = self.question_repo.create(question_model)
            saved_questions += 1
            
            # Save related subquestions
            for sq in q_data.subquestions:
                self.subquestion_repo.create(Subquestion(
                    question_id=saved_q.id,
                    identifier=sq.subquestion_identifier,
                    text=sq.text,
                    marks=sq.marks
                ))
            
            # Save related diagrams
            if q_data.image_url:
                self.diagram_repo.create(Diagram(
                    question_id=saved_q.id,
                    diagram_url=q_data.image_url,
                    description=f"Diagram for question {q_data.question_number}"
                ))

            for d in q_data.diagrams:
                self.diagram_repo.create(Diagram(
                    question_id=saved_q.id,
                    diagram_url="PENDING_UPLOAD", # To be implemented in Storage
                    description=d.description
                ))
                
            # Save related figures
            for f in q_data.figures:
                self.figure_repo.create(Figure(
                    question_id=saved_q.id,
                    figure_type=f.figure_type,
                    data_source="PENDING_UPLOAD" # To be implemented in Storage
                ))

        return {
            "status": "success",
            "message": f"Successfully mapped and saved {saved_questions} questions into Collections."
        }
