import ast
import tree_sitter
from pathlib import Path
from typing import Dict, List, Any
import git

class CodeAnalyzer:
    """Multi-language code analyzer using AST parsing"""
    
    def __init__(self):
        self.parsers = {}
        self._init_parsers()
    
    def _init_parsers(self):
        """Initialize tree-sitter parsers for supported languages"""
        try:
            # Tree-sitter setup (simplified - in production, load compiled parsers)
            pass
        except Exception as e:
            print(f"Parser initialization warning: {e}")
    
    def analyze_repository(self, repo_path: str) -> Dict[str, Any]:
        """Analyze entire repository structure"""
        repo = git.Repo(repo_path)
        
        analysis = {
            "repository": str(repo_path),
            "modules": [],
            "services": [],
            "apis": [],
            "dependencies": [],
            "entry_points": [],
            "architecture": {}
        }
        
        # Detect language
        language = self._detect_language(repo_path)

        analysis["language"] = language
        
        # Parse files based on language
        if language == "python":
            analysis.update(self._analyze_python(repo_path))
        elif language in ["javascript", "typescript"]:
            analysis.update(self._analyze_javascript(repo_path))
        
        # Analyze Git history
        analysis["git_history"] = self._analyze_git_history(repo)

        return analysis
    
    def _detect_language(self, repo_path: str) -> str:
        """Detect primary language of repository"""
        path = Path(repo_path)
        
        # Count file extensions
        extensions = {}
        for file in path.rglob("*"):
            if file.is_file():
                ext = file.suffix
                extensions[ext] = extensions.get(ext, 0) + 1
        
        # Map extensions to languages
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".go": "go"
        }
        
        primary_ext = max(extensions.items(), key=lambda x: x[1])[0] if extensions else ".py"
        return lang_map.get(primary_ext, "unknown")
    
    def _analyze_python(self, repo_path: str) -> Dict[str, Any]:
        """Analyze Python codebase"""
        path = Path(repo_path)
        modules = []
        classes = []
        functions = []
        apis = []
        call_edges = []
        features = []
        feature_map = {}
        
        for py_file in path.rglob("*.py"):
            if "venv" in str(py_file) or "site-packages" in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                module_doc = ast.get_docstring(tree) or ""
                module_info = {
                    "name": py_file.stem,
                    "path": str(py_file.relative_to(path)),
                    "classes": [],
                    "functions": [],
                    "imports": [],
                    "docstring": module_doc
                }
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_info = {
                            "name": node.name,
                            "methods": [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                            "bases": [self._get_name(b) for b in node.bases],
                            "docstring": ast.get_docstring(node) or ""
                        }
                        module_info["classes"].append(class_info)
                        classes.append(class_info)
                    
                    elif isinstance(node, ast.FunctionDef):
                        func_info = {
                            "name": node.name,
                            "args": [arg.arg for arg in node.args.args],
                            "decorators": [self._get_name(d) for d in node.decorator_list],
                            "docstring": ast.get_docstring(node) or "",
                            "module_path": module_info["path"],
                            "returns": self._get_name(node.returns) if getattr(node, "returns", None) else None
                        }
                        module_info["functions"].append(func_info)
                        functions.append(func_info)
                        
                        # Collect call graph edges within this function
                        for inner in ast.walk(node):
                            if isinstance(inner, ast.Call):
                                target = self._get_name(inner.func)
                                source_id = f"{module_info['path']}::{node.name}"
                                target_id = f"{module_info['path']}::{target.split('.')[-1]}"
                                call_edges.append({"from": source_id, "to": target_id})
                        
                        # Detect API endpoints (FastAPI/Flask patterns)
                        if any(d in ["app.get", "app.post", "route"] for d in func_info["decorators"]):
                            apis.append({
                                "endpoint": node.name,
                                "file": str(py_file.relative_to(path)),
                                "type": "REST"
                            })
                    
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            module_info["imports"].extend([alias.name for alias in node.names])
                        else:
                            module_info["imports"].append(node.module)
                
                modules.append(module_info)
                
                # Simple feature extraction heuristic based on filenames and docstrings
                keywords = ["auth", "login", "user", "api", "request", "response",
                            "db", "database", "cache", "graph", "neo4j", "docs",
                            "generate", "analyze", "nlp", "task", "worker"]
                matched = [k for k in keywords if k in (module_info["name"].lower() + " " + module_doc.lower())]
                for k in matched:
                    if k not in feature_map:
                        feature_map[k] = {"name": k, "functions": []}
                    for f in module_info["functions"]:
                        feature_map[k]["functions"].append(f"{module_info['path']}::{f['name']}")
            
            except Exception as e:
                print(f"Error parsing {py_file}: {e}")
        
        features = list(feature_map.values())
        return {
            "modules": modules,
            "classes": classes,
            "functions": functions,
            "apis": apis,
            "call_edges": call_edges,
            "features": features
        }
    
    def _analyze_javascript(self, repo_path: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript codebase"""
        # Simplified - in production, use Babel parser
        return {"modules": [], "components": [], "apis": []}
    
    def _get_name(self, node) -> str:
        """Extract name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def _analyze_git_history(self, repo: git.Repo, limit: int = 100) -> List[Dict]:
        """Analyze recent Git commits"""
        commits = []
        
        for commit in list(repo.iter_commits())[:limit]:
            commit_info = {
                "sha": commit.hexsha,
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip(),
                "files_changed": len(commit.stats.files),
                "insertions": commit.stats.total["insertions"],
                "deletions": commit.stats.total["deletions"]
            }
            commits.append(commit_info)
        
        return commits
