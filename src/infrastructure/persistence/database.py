import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.domain.models import Base, ReviewHistoryEntity

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/reviewflow")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

class ReviewRepository:
    @staticmethod
    def create_history(repo_name: str, pr_id: int, commit_sha: str) -> int:
        db = SessionLocal()
        try:
            history = ReviewHistoryEntity(
                repo_name=repo_name,
                pr_id=pr_id,
                commit_sha=commit_sha,
                status="PENDING"
            )
            db.add(history)
            db.commit()
            db.refresh(history)
            return history.id
        finally:
            db.close()

    @staticmethod
    def update_status(history_id: int, status: str, total_tokens: int = 0, cost: float = 0.0, summary: str = None, error: str = None):
        db = SessionLocal()
        try:
            history = db.query(ReviewHistoryEntity).filter(ReviewHistoryEntity.id == history_id).first()
            if history:
                history.status = status
                history.total_tokens += total_tokens
                history.estimated_cost += cost
                if summary: history.summary = summary
                if error: history.error_message = error
                db.commit()
        finally:
            db.close()