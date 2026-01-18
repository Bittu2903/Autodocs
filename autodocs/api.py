from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
import re
import asyncio

from core.config import settings
from features.code_analyzer import CodeAnalyzer
from features.doc_generator import DocumentGenerator
from features.knowledge_graph import KnowledgeGraph
from features.nlp_processor import NLPProcessor
from models.models import AnalysisJob, Base, Document, Repository

app = FastAPI(title="AI Documentation Generator", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
engine = create_engine(settings.POSTGRES_URI)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# Knowledge Graph
kg = KnowledgeGraph(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)

# Analyzers
code_analyzer = CodeAnalyzer()
nlp_processor = NLPProcessor(settings.ANTHROPIC_API_KEY)
doc_generator = DocumentGenerator(nlp_processor)

# Request Models
class RepositoryCreate(BaseModel):
    name: str
    url: str
    branch: str = "main"

class DocumentQuery(BaseModel):
    doc_type: Optional[str] = None

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Background Tasks
def _sanitize_url(url: str) -> str:
    return url.strip().strip("`").strip('"').strip("'")

def _with_github_token(url: str, token: Optional[str]) -> str:
    if not token:
        return url
    # Only rewrite GitHub https URLs
    m = re.match(r"^https://github.com/(.+)$", url)
    if not m:
        return url
    # Embed token for PAT auth
    # Format: https://<token>@github.com/owner/repo(.git)
    if url.endswith(".git"):
        return f"https://{token}@github.com/{m.group(1)}"
    return f"https://{token}@github.com/{m.group(1)}.git"

async def analyze_repository_task(repo_id: str, repo_url: str, db_session):
    """Background task to analyze repository"""
    import tempfile
    import shutil
    import git
    
    # Update job status
    job = db_session.query(AnalysisJob).filter(AnalysisJob.repository_id == repo_id).first()
    job.status = "running"
    job.started_at = datetime.utcnow()
    db_session.commit()
    
    try:
        # Clone repository
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = f"{tmpdir}/repo"
            clean_url = _sanitize_url(repo_url)
            try:
                git.Repo.clone_from(clean_url, repo_path)
            except Exception as e:
                # Retry with GitHub token if available
                token_url = _with_github_token(clean_url, settings.GITHUB_TOKEN)
                if token_url != clean_url:
                    git.Repo.clone_from(token_url, repo_path)
                else:
                    raise
            
            # Analyze code
            analysis = code_analyzer.analyze_repository(repo_path)
            
            # Store in knowledge graph
            kg.store_analysis(repo_id, analysis)
            
            # Generate documents
            arch_doc = doc_generator.generate_architecture_doc(
                analysis, 
                kg.get_architecture_overview(repo_id)
            )
            
            # Save architecture doc
            doc = Document(
                repository_id=repo_id,
                doc_type="architecture",
                title="Architecture Overview",
                content=arch_doc,
                confidence_score=85
            )
            db_session.add(doc)
            
            # Generate changelog
            changelog = doc_generator.generate_changelog(analysis.get('git_history', []))
            doc = Document(
                repository_id=repo_id,
                doc_type="changelog",
                title="Recent Changes",
                content=changelog,
                confidence_score=90
            )
            db_session.add(doc)
            
            # Generate onboarding
            onboarding = doc_generator.generate_onboarding_doc(analysis)
            doc = Document(
                repository_id=repo_id,
                doc_type="onboarding",
                title="Getting Started",
                content=onboarding,
                confidence_score=80
            )
            db_session.add(doc)
            
            comprehensive = doc_generator.generate_comprehensive_doc(analysis)
            doc = Document(
                repository_id=repo_id,
                doc_type="comprehensive",
                title="Comprehensive Documentation",
                content=comprehensive,
                confidence_score=75
            )
            db_session.add(doc)
            
            # Update job
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.progress = 100
            job.result = {"modules": len(analysis.get('modules', []))}
            
            # Update repository
            repo = db_session.query(Repository).filter(Repository.id == repo_id).first()
            repo.status = "analyzed"
            repo.last_analyzed = datetime.utcnow()
            repo.language = analysis.get('language')
            
            db_session.commit()
    
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db_session.commit()

# API Endpoints
@app.get("/")
async def root():
    return {"message": "AI Documentation Generator API", "version": "1.0.0"}

@app.post("/api/repositories")
async def create_repository(
    repo: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Add a new repository to analyze"""
    # Create repository
    clean_url = _sanitize_url(repo.url)
    db_repo = Repository(
        name=repo.name,
        url=clean_url,
        branch=repo.branch,
        status="pending"
    )
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    
    # Create analysis job
    job = AnalysisJob(
        repository_id=db_repo.id,
        job_type="full_scan",
        status="pending"
    )
    db.add(job)
    db.commit()
    
    # Start background analysis
    background_tasks.add_task(analyze_repository_task, db_repo.id, clean_url, db)
    
    return {
        "id": db_repo.id,
        "name": db_repo.name,
        "status": "analyzing",
        "message": "Repository analysis started"
    }

@app.get("/api/repositories")
async def list_repositories(db: Session = Depends(get_db)):
    """List all repositories"""
    repos = db.query(Repository).all()
    return repos

@app.get("/api/repositories/{repo_id}")
async def get_repository(repo_id: str, db: Session = Depends(get_db)):
    """Get repository details"""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Get analysis job
    job = db.query(AnalysisJob).filter(
        AnalysisJob.repository_id == repo_id
    ).order_by(AnalysisJob.created_at.desc()).first()
    
    return {
        "repository": repo,
        "analysis_job": job
    }

@app.get("/api/repositories/{repo_id}/documents")
async def list_documents(repo_id: str, doc_type: Optional[str] = None, db: Session = Depends(get_db)):
    """List documents for a repository"""
    query = db.query(Document).filter(Document.repository_id == repo_id)
    
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    
    docs = query.all()
    return docs

@app.get("/api/repositories/{repo_id}/documents/{doc_id}")
async def get_document(repo_id: str, doc_id: str, db: Session = Depends(get_db)):
    """Get a specific document"""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.repository_id == repo_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc

@app.get("/api/repositories/{repo_id}/architecture")
async def get_architecture(repo_id: str):
    """Get architecture overview from knowledge graph"""
    architecture = kg.get_architecture_overview(repo_id)
    return architecture

@app.post("/api/repositories/{repo_id}/regenerate")
async def regenerate_docs(
    repo_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Regenerate documentation for a repository"""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Create new analysis job
    job = AnalysisJob(
        repository_id=repo_id,
        job_type="full_scan",
        status="pending"
    )
    db.add(job)
    db.commit()
    
    # Start background task
    background_tasks.add_task(analyze_repository_task, repo_id, repo.url, db)
    
    return {"message": "Documentation regeneration started"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "knowledge_graph": "connected"
    }

@app.delete("/api/repositories/{repo_id}")
async def delete_repository(repo_id: str, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    db.query(Document).filter(Document.repository_id == repo_id).delete()
    db.query(AnalysisJob).filter(AnalysisJob.repository_id == repo_id).delete()
    kg.delete_repository(repo_id)
    db.delete(repo)
    db.commit()
    return {"message": "Repository deleted"}

@app.get("/api/repositories/{repo_id}/graph")
async def get_graph(repo_id: str):
    return kg.get_graph(repo_id)

@app.get("/api/graph/nodes/{node_id}/neighbors")
async def get_neighbors(node_id: str):
    return kg.get_neighbors(node_id)
