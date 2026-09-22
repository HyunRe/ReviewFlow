from datetime import datetime
from typing import List, Optional
from typing_extensions import TypedDict
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# --- PostgreSQL ORM Entity ---
class ReviewHistoryEntity(Base):
    __tablename__ = "review_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_name = Column(String(255), nullable=False)
    pr_id = Column(Integer, nullable=False)
    commit_sha = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, IN_PROGRESS, SUCCESS, FAILED
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)  # 달러 ($) 기준 비용
    summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# --- LangGraph Review State ---
class ReviewState(TypedDict):
    review_history_id: int
    pr_id: int
    repo_name: str
    commit_sha: str
    raw_diff: str
    filtered_diff: str
    file_list: List[str]

    has_security_risk: bool
    has_performance_risk: bool

    security_review: Optional[str]
    performance_review: Optional[str]
    style_review: Optional[str]
    final_summary: str

    # 토큰 및 비용 집계
    total_tokens: int
    estimated_cost: float