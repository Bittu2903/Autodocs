from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    branch = Column(String, default="main")
    language = Column(String)
    last_analyzed = Column(DateTime)
    status = Column(String, default="pending")
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    documents = relationship("Document", back_populates="repository")
    analysis_jobs = relationship("AnalysisJob", back_populates="repository")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id"))
    doc_type = Column(String)  # architecture, api, adr, changelog, onboarding
    title = Column(String)
    content = Column(Text)
    version = Column(Integer, default=1)
    auto_generated = Column(Boolean, default=True)
    confidence_score = Column(Integer)  # 0-100
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    repository = relationship("Repository", back_populates="documents")

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id"))
    job_type = Column(String)  # full_scan, incremental, git_update
    status = Column(String)  # pending, running, completed, failed
    progress = Column(Integer, default=0)
    result = Column(JSON)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    repository = relationship("Repository", back_populates="analysis_jobs")