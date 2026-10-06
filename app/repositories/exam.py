from datetime import UTC, datetime

from google.cloud.firestore import Client, FieldFilter

from app.models.exam import (
    Diagram,
    Figure,
    Question,
    Subject,
    Subquestion,
    SubSubquestion,
    Topic,
    Year,
)
from app.repositories.base import BaseRepository
from app.schemas.exam import (
    DiagramData,
    ExamPaperData,
    FigureData,
    QuestionData,
    SubquestionData,
    SubSubquestionData,
)


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
        self.sub_subquestion_repo = BaseRepository(
            db, SubSubquestion, "sub_subquestions"
        )
        self.diagram_repo = BaseRepository(db, Diagram, "diagrams")
        self.figure_repo = BaseRepository(db, Figure, "figures")

    def _ensure_year_exists(self, year_num: int, subject_name: str) -> None:
        """Creates or updates a year document."""
        year_id = str(year_num)
        year_doc = self.year_repo.get(year_id)

        if not year_doc:
            self.year_repo.create(
                Year(year=year_num, name=[subject_name]), doc_id=year_id
            )
        else:
            if subject_name not in year_doc.name:
                updated_names = year_doc.name + [subject_name]
                self.year_repo.update(year_id, {"name": updated_names})

    def _ensure_subject_exists(self, subject_name: str, level: str) -> None:
        """Creates a subject document if it doesn't exist."""
        subject_id = subject_name.lower().replace(" ", "_")
        subject_doc = self.subject_repo.get(subject_id)

        if not subject_doc:
            self.subject_repo.create(
                Subject(name=subject_name, level=level), doc_id=subject_id
            )

    def _ensure_topic_exists(self, topic_name: str, subtopic_name: str) -> None:
        """Creates or updates a topic document."""
        topic_id = topic_name.lower().replace(" ", "_")
        topic_doc = self.topic_repo.get(topic_id)

        if not topic_doc:
            self.topic_repo.create(
                Topic(name=topic_name, subtopics=[subtopic_name]), doc_id=topic_id
            )
        else:
            if subtopic_name not in topic_doc.subtopics:
                updated_subtopics = topic_doc.subtopics + [subtopic_name]
                self.topic_repo.update(topic_id, {"subtopics": updated_subtopics})

    def check_exam_exists(self, subject: str, year: int, paper: int) -> bool:
        """
        Query the questions collection to see if any questions match
        the combination of subject, year, and paper.
        """
        docs = (
            self.question_repo.collection.where(filter=FieldFilter("year", "==", year))
            .where(filter=FieldFilter("paper", "==", paper))
            .stream()
        )
        # return True if the stream yields any match
        for doc in docs:
            data = doc.to_dict()
            if data.get("subject", "").lower() == subject.lower():
                return True
        return False

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
                has_subquestions=q_data.has_subquestions
                or len(q_data.subquestions) > 0,
                question_text=q_data.question_text,
                topic=q_data.topic,
                subtopic=q_data.subtopic,
                marks_total=q_data.marks_total,
                question_type=q_data.question_type,
                has_diagram=q_data.has_diagram,
                has_figure=q_data.has_figure,
            )

            # Save parent question to get its ID
            saved_q = self.question_repo.create(question_model)
            saved_questions += 1

            # Save related subquestions
            for sq in q_data.subquestions:
                saved_sq = self.subquestion_repo.create(
                    Subquestion(
                        question_id=saved_q.id,
                        identifier=sq.subquestion_identifier,
                        text=sq.text,
                        marks=sq.marks,
                        image_url=sq.image_url,
                    )
                )

                # Save deeper sub-sub-questions (e.g., 1(a)(iii)) with their images
                for ssq in sq.sub_subquestions:
                    self.sub_subquestion_repo.create(
                        SubSubquestion(
                            subquestion_id=saved_sq.id,
                            identifier=ssq.sub_subquestion_identifier,
                            text=ssq.text,
                            marks=ssq.marks,
                            image_url=ssq.image_url,
                        )
                    )

            # Save related diagrams
            if q_data.image_url:
                self.diagram_repo.create(
                    Diagram(
                        question_id=saved_q.id,
                        diagram_url=q_data.image_url,
                        description=f"Diagram for question {q_data.question_number}",
                    )
                )

            for d in q_data.diagrams:
                self.diagram_repo.create(
                    Diagram(
                        question_id=saved_q.id,
                        diagram_url="PENDING_UPLOAD",  # To be implemented in Storage
                        description=d.description,
                    )
                )

            for f in q_data.figures:
                self.figure_repo.create(
                    Figure(
                        question_id=saved_q.id,
                        figure_type=f.figure_type,
                        data_source="PENDING_UPLOAD",  # To be implemented in Storage
                    )
                )

        # 3. Maintain Exam Metadata for faster listing
        self._update_exam_metadata(exam_data.subject, exam_data.year, exam_data.paper)

        return {
            "status": "success",
            "message": f"Successfully mapped and saved {saved_questions} questions into Collections.",
        }

    def _update_exam_metadata(self, subject: str, year: int, paper: int) -> None:
        """Updates a central metadata document for unique exams."""
        metadata_ref = self.db.collection("exam_metadata").document(
            f"{subject}_{year}_{paper}".lower().replace(" ", "_")
        )
        metadata_ref.set(
            {
                "subject": subject,
                "year": year,
                "paper": paper,
                "updated_at": datetime.now(UTC),
            }
        )

    def get_all_exams(self) -> list[dict]:
        """
        Fetches all unique combinations of subject, year, and paper available in the database.
        Uses the optimized exam_metadata collection.
        """
        metadata_docs = self.db.collection("exam_metadata").stream()

        unique_exams = []
        for doc in metadata_docs:
            data = doc.to_dict()
            unique_exams.append(
                {
                    "subject": data["subject"],
                    "year": data["year"],
                    "paper": data["paper"],
                    "pdf_path": data.get("pdf_path"),
                    "pdf_url": data.get("pdf_url"),
                }
            )

        if unique_exams:
            return sorted(
                unique_exams, key=lambda x: (x["subject"], x["year"], x["paper"])
            )

        # Fallback to the slow method only if metadata is empty (for backward compatibility)
        questions = self.question_repo.list_all()
        unique_set = set()
        for q in questions:
            unique_set.add((q.subject, q.year, q.paper))

        return [
            {"subject": s, "year": y, "paper": p, "pdf_url": None}
            for s, y, p in sorted(unique_set)
        ]

    def get_full_exam(
        self, subject: str, year: int, paper: int
    ) -> ExamPaperData | None:
        """
        Reconstructs a full ExamPaperData object for a specific subject/year/paper.
        """
        # 1. Fetch all questions for this exam
        # Fetching by year and paper first to allow case-insensitive subject matching in Python
        questions_stream = (
            self.question_repo.collection.where(filter=FieldFilter("year", "==", year))
            .where(filter=FieldFilter("paper", "==", paper))
            .stream()
        )

        question_docs = []
        for doc in questions_stream:
            data = doc.to_dict()
            if data.get("subject", "").lower() == subject.lower():
                q_model = Question(**{**data, "id": doc.id})
                question_docs.append(q_model)

        if not question_docs:
            return None

        # Sort questions by question_number (may need natural sort if they are strings like '1a')
        question_docs.sort(key=lambda x: str(x.question_number))

        # 2. Bulk fetch all related entities for these questions
        question_ids = [q.id for q in question_docs]

        # Fetch all subquestions for all questions in this exam
        all_subquestions = self.subquestion_repo.get_by_field_in_values(
            "question_id", question_ids
        )
        # Fetch all sub-sub-questions nested under those subquestions
        all_sub_subquestions = self.sub_subquestion_repo.get_by_field_in_values(
            "subquestion_id", [sq.id for sq in all_subquestions]
        )
        # Fetch all diagrams
        all_diagrams = self.diagram_repo.get_by_field_in_values(
            "question_id", question_ids
        )
        # Fetch all figures
        all_figures = self.figure_repo.get_by_field_in_values(
            "question_id", question_ids
        )

        # Group related entities by question_id for O(1) lookup
        sub_by_q = {}
        ssq_by_sub = {}
        diag_by_q = {}
        fig_by_q = {}

        for sq in all_subquestions:
            sub_by_q.setdefault(sq.question_id, []).append(sq)
        for ssq in all_sub_subquestions:
            ssq_by_sub.setdefault(ssq.subquestion_id, []).append(ssq)
        for d in all_diagrams:
            diag_by_q.setdefault(d.question_id, []).append(d)
        for f in all_figures:
            fig_by_q.setdefault(f.question_id, []).append(f)

        # 3. Reconstruct QuestionData for each question
        reconstructed_questions = []
        topics_covered = set()

        for q in question_docs:
            topics_covered.add(q.topic)

            # Get pre-fetched related entities
            subquestions = sub_by_q.get(q.id, [])
            subquestions.sort(key=lambda x: x.identifier)

            diagrams = diag_by_q.get(q.id, [])
            figures = fig_by_q.get(q.id, [])

            # Map models to Schemas
            q_data = QuestionData(
                question_number=q.question_number,
                question_text=q.question_text,
                topic=q.topic,
                subtopic=q.subtopic,
                marks_total=q.marks_total,
                question_type=q.question_type,
                has_diagram=q.has_diagram,
                image_url=diagrams[0].diagram_url if diagrams else None,
                has_figure=q.has_figure,
                has_subquestions=q.has_subquestions,
                subquestions=[
                    SubquestionData(
                        subquestion_identifier=sq.identifier,
                        text=sq.text,
                        marks=sq.marks or 0,
                        image_url=sq.image_url,
                        sub_subquestions=[
                            SubSubquestionData(
                                sub_subquestion_identifier=ssq.identifier,
                                text=ssq.text,
                                marks=ssq.marks or 0,
                                image_url=ssq.image_url,
                            )
                            for ssq in sorted(
                                ssq_by_sub.get(sq.id, []),
                                key=lambda x: x.identifier,
                            )
                        ],
                    )
                    for sq in subquestions
                ],
                diagrams=[DiagramData(description=d.description) for d in diagrams],
                figures=[FigureData(figure_type=f.figure_type) for f in figures],
            )
            reconstructed_questions.append(q_data)

        # 3. Create full ExamPaperData
        # We need the level too; we can get it from the Subject model if needed
        subject_id = subject.lower().replace(" ", "_")
        subject_doc = self.subject_repo.get(subject_id)
        level = subject_doc.level if subject_doc else "Unknown"

        return ExamPaperData(
            subject=question_docs[0].subject if question_docs else subject,
            level=level,
            year=year,
            paper=paper,
            topics_covered=list(topics_covered),
            questions=reconstructed_questions,
        )
