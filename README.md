# Autodocs: AI-Enhanced Documentation Generator

Autodocs analyzes codebases to generate architecture documentation, changelogs, onboarding guides, and comprehensive docs. It builds a live knowledge graph of modules, classes, functions, APIs, and features; visualizes one-to-one, one-to-many, and many-to-many relationships; and keeps documentation up to date by tracking code structure and git changes.

## Features
- End-to-end analysis of repositories and branches (Python-first, extensible to other languages)
- Generated docs:
  - Architecture Overview
  - Recent Changes (from Git history, grouped by intent)
  - Getting Started (Onboarding)
  - Comprehensive Documentation (modules, features, imports, workflows)
- Interactive Graph:
  - Nodes: Repository, Module, Class, Function, API, Feature
  - Edges: CONTAINS, DEFINES, EXPOSES, CALLS, HAS_FEATURE, INCLUDES
  - Click a node to expand neighbors and discover dependencies
- Backend APIs (FastAPI) and frontend (React) UI
- Neo4j knowledge graph, PostgreSQL storage, Redis cache

## Stack
- Backend: FastAPI (Python 3.11), SQLAlchemy
- Datastores: PostgreSQL, Redis, Neo4j
- Frontend: React (Create React App), react-force-graph, axios, lucide-react
- Containers: Docker Compose

## Quick Start
- Requirements: Docker, Docker Compose
- Start services:

```bash
docker compose up -d --build
```

- Open:
  - Frontend: http://localhost:3000
  - Backend: http://localhost:8000 (Swagger: http://localhost:8000/docs)
  - Neo4j Browser: http://localhost:7474
  - PostgreSQL: localhost:5433 (container listens on 5432)
  - Redis: localhost:6379

## Configuration
- Compose service environment (backend) [docker-compose.yml](file:///Users/singh/Desktop/Personal%20Workspace/docker-compose.yml)
  - NEO4J_URI=bolt://neo4j:7687
  - NEO4J_USER=neo4j
  - NEO4J_PASSWORD=password
  - POSTGRES_URI=postgresql://postgres:12345@postgres:5432/docgen
  - REDIS_URL=redis://redis:6379/0
  - GITHUB_TOKEN=${GITHUB_TOKEN:-} (optional for private repos)
- Frontend environment:
  - REACT_APP_API_URL=http://localhost:8000
  - CHOKIDAR_USEPOLLING=true
- Optional:
  - ANTHROPIC_API_KEY in backend env for richer NLP summaries

## Usage
- Add a repository from UI or via API:

```bash
curl -X POST http://localhost:8000/api/repositories \
  -H 'Content-Type: application/json' \
  -d '{"name":"my repo","url":"https://github.com/owner/repo","branch":"main"}'
```

- View repositories:

```bash
curl http://localhost:8000/api/repositories
```

- Get repository details:

```bash
curl http://localhost:8000/api/repositories/<repo_id>
```

- List documents:

```bash
curl http://localhost:8000/api/repositories/<repo_id>/documents
```

- Regenerate documentation:

```bash
curl -X POST http://localhost:8000/api/repositories/<repo_id>/regenerate
```

- Delete a repository:

```bash
curl -X DELETE http://localhost:8000/api/repositories/<repo_id>
```

- Graph endpoints:

```bash
# Initial graph snapshot
curl http://localhost:8000/api/repositories/<repo_id>/graph

# Expand a node's neighbors
curl http://localhost:8000/api/graph/nodes/<node_id>/neighbors
```

## Frontend
- Sidebar: repositories list with status and language
- Repo header: Regenerate and Delete actions
- Tabs:
  - Documents: shows generated docs
  - Graph: interactive force-directed graph
    - Click nodes to expand neighbors
    - Color by node type; tooltips show type and label

## Data Model
- Repository: id, name, url, branch, language, status, last_analyzed
- Document: id, repository_id, doc_type, title, content, confidence_score, metadata
- AnalysisJob: id, repository_id, job_type, status, progress, result, error_message, timestamps
References: [models.py](file:///Users/singh/Desktop/Personal%20Workspace/autodocs/models/models.py)

## Knowledge Graph Schema
- Nodes:
  - Repository
  - Module (name, path, docstring)
  - Class (name, docstring)
  - Function (name, args, returns, docstring, path)
  - API (endpoint, type, file)
  - Feature (heuristic grouping)
- Relationships:
  - Repository -[:CONTAINS]-> Module
  - Module -[:DEFINES]-> Class / Function
  - Function -[:CALLS]-> Function
  - Repository -[:EXPOSES]-> API
  - Repository -[:HAS_FEATURE]-> Feature
  - Feature -[:INCLUDES]-> Function
References: [knowledge_graph.py](file:///Users/singh/Desktop/Personal%20Workspace/autodocs/features/knowledge_graph.py)

## Analysis
- Language detection by dominant file extension
- Python parsing via AST:
  - Collect module/class/function docstrings and signatures
  - Detect intra-module function calls to build call graph
  - Heuristic feature extraction by keywords across names/docstrings
- Git history analysis for changelog grouping by intent
References: [code_analyzer.py](file:///Users/singh/Desktop/Personal%20Workspace/autodocs/features/code_analyzer.py)

## Document Generation
- Architecture Overview (modules, APIs, diagram)
- Changelog (grouped by feature/bugfix/refactor/etc.)
- Onboarding (project entry points and key modules)
- Comprehensive Documentation (modules, feature-related functions, imports, workflows)
References: [doc_generator.py](file:///Users/singh/Desktop/Personal%20Workspace/autodocs/features/doc_generator.py)

## Troubleshooting
- Postgres port conflict: host uses 5433 -> 5432 container; ensure 5433 is free
- Private GitHub repos: set GITHUB_TOKEN in environment (PAT with repo access)
- No nodes in graph:
  - Run analysis on a Python repo (JS/TS parsing is stubbed)
  - Ensure docstrings and function calls exist to populate the graph
- Neo4j warnings on labels/relationships:
  - Graph builds as analysis runs; missing labels initially are okay during early queries

## Development Notes
- Backend runs with uvicorn reload inside the container
- Frontend runs CRA dev server inside Node container
- For production frontend, build static assets and serve via nginx

## Roadmap
- JS/TS, Java, Go parsing with robust call graphs
- Semantic feature detection via NLP over docstrings and commit messages
- Markdown rendering of document content in UI
- Side panel for node details (params, returns, docstring summary)
- Webhooks for auto-regeneration on push/PRs

