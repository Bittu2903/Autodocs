from datetime import datetime
from typing import Dict, List, Any
import json

from features.nlp_processor import NLPProcessor

class DocumentGenerator:
    """Generate various types of documentation"""
    
    def __init__(self, nlp_processor: NLPProcessor = None):
        self.nlp = nlp_processor or NLPProcessor()
    
    def generate_comprehensive_doc(self, analysis: Dict[str, Any]) -> str:
        doc = f"# Comprehensive Documentation\n"
        doc += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        doc += f"## Overview\n\n"
        doc += f"This project is primarily {analysis.get('language', 'unknown')}.\n"
        doc += f"It contains {len(analysis.get('modules', []))} modules, "
        doc += f"{len(analysis.get('classes', []))} classes, and {len(analysis.get('functions', []))} functions.\n\n"
        doc += f"## Modules\n\n"
        for module in analysis.get('modules', [])[:30]:
            doc += f"### {module['name']}\n"
            if module.get('docstring'):
                summary = self.nlp.generate_summary(module['docstring'], 240)
                doc += f"{summary}\n"
            doc += f"- Path: `{module['path']}`\n"
            doc += f"- Classes: {len(module.get('classes', []))}\n"
            doc += f"- Functions: {len(module.get('functions', []))}\n"
            features = []
            for f in module.get('functions', []):
                n = f['name'].lower()
                if any(k in n for k in ['add', 'create', 'update', 'delete', 'render', 'parse', 'fetch', 'handle', 'process']):
                    features.append(n)
            if features:
                doc += f"- Feature-related functions: {', '.join(sorted(set(features))[:10])}\n"
            doc += "\n"
        doc += f"## APIs\n\n"
        if analysis.get('apis'):
            for api in analysis.get('apis', []):
                doc += f"- {api.get('endpoint')} ({api.get('type','REST')})\n"
        else:
            doc += "No REST API endpoints were detected in static analysis.\n"
        doc += "\n## Dependencies and Imports\n\n"
        imports = {}
        for m in analysis.get('modules', []):
            for imp in m.get('imports', []):
                imports[imp] = imports.get(imp, 0) + 1
        top_imports = sorted(imports.items(), key=lambda x: x[1], reverse=True)[:15]
        for imp, count in top_imports:
            doc += f"- {imp} ({count} uses)\n"
        doc += "\n## Workflows and Changes\n\n"
        if analysis.get('git_history'):
            doc += self.generate_changelog(analysis['git_history'])
        else:
            doc += "No recent git history available.\n"
        return doc
    
    def generate_architecture_doc(self, analysis: Dict[str, Any], 
                                   architecture: Dict[str, Any]) -> str:
        """Generate architecture documentation"""
        doc = f"""# Architecture Documentation
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Auto-generated:** Yes

## System Overview

This system is a {analysis.get('language', 'multi-language')} application with {len(analysis.get('modules', []))} modules and {len(analysis.get('apis', []))} API endpoints.

## Components

### Modules
"""
        
        for module in analysis.get('modules', [])[:10]:  # Top 10
            doc += f"\n#### {module['name']}\n"
            doc += f"- **Path:** `{module['path']}`\n"
            doc += f"- **Classes:** {len(module.get('classes', []))}\n"
            doc += f"- **Functions:** {len(module.get('functions', []))}\n"
        
        doc += "\n## API Endpoints\n\n"
        
        for api in analysis.get('apis', []):
            doc += f"- **{api['endpoint']}** ({api.get('type', 'REST')})\n"
            doc += f"  - File: `{api.get('file', 'unknown')}`\n"
        
        doc += "\n## Architecture Diagram\n\n"
        doc += self._generate_mermaid_diagram(architecture)
        
        return doc
    
    def _generate_mermaid_diagram(self, architecture: Dict[str, Any]) -> str:
        """Generate Mermaid diagram from architecture"""
        diagram = "```mermaid\ngraph TD\n"
        
        # Add modules
        for idx, module in enumerate(architecture.get('modules', [])[:5]):
            diagram += f"    M{idx}[{module.get('name', 'Module')}]\n"
        
        # Add APIs
        for idx, api in enumerate(architecture.get('apis', [])[:3]):
            diagram += f"    A{idx}[{api.get('endpoint', 'API')}]\n"
            diagram += f"    M0 --> A{idx}\n"
        
        diagram += "```\n"
        return diagram
    
    def generate_api_doc(self, apis: List[Dict[str, Any]]) -> str:
        """Generate API documentation"""
        doc = f"""# API Documentation
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Endpoints

"""
        
        for api in apis:
            doc += f"### {api['endpoint']}\n\n"
            doc += f"- **Type:** {api.get('type', 'REST')}\n"
            doc += f"- **File:** `{api.get('file', 'unknown')}`\n"
            doc += f"- **Methods:** {', '.join(api.get('methods', ['GET']))}\n\n"
        
        return doc
    
    def generate_changelog(self, commits: List[Dict[str, Any]]) -> str:
        """Generate changelog from commits"""
        doc = f"""# Changelog
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Recent Changes

"""
        
        # Group by intent type
        grouped = {}
        for commit in commits[:50]:  # Last 50 commits
            intent = self.nlp.extract_intent(commit['message'])
            intent_type = intent['type']
            
            if intent_type not in grouped:
                grouped[intent_type] = []
            grouped[intent_type].append(commit)
        
        # Write grouped changes
        type_names = {
            "feature": "✨ Features",
            "bugfix": "🐛 Bug Fixes",
            "refactor": "♻️ Refactoring",
            "documentation": "📝 Documentation",
            "other": "🔧 Other Changes"
        }
        
        for intent_type, commits in grouped.items():
            doc += f"\n### {type_names.get(intent_type, intent_type.title())}\n\n"
            for commit in commits[:10]:
                date = commit['date'][:10]
                message = commit['message'].split('\n')[0][:100]
                doc += f"- [{date}] {message} ({commit['sha'][:7]})\n"
        
        return doc
    
    def generate_adr(self, pr_analysis: Dict[str, Any], commit_data: Dict[str, Any]) -> str:
        """Generate Architecture Decision Record"""
        doc = f"""# ADR: {pr_analysis.get('title', 'Untitled Decision')}

**Date:** {datetime.now().strftime("%Y-%m-%d")}
**Status:** Accepted
**Auto-generated:** Yes (Confidence: 75%)

## Context

{pr_analysis.get('rationale', 'Decision context extracted from PR and commit history.')}

## Decision

{pr_analysis.get('decisions', ['Decision details extracted from discussion.'])[0] if pr_analysis.get('decisions') else 'See discussion for details.'}

## Consequences

### Positive
- Implementation completed in PR
- Code review approved

### Negative
- {pr_analysis.get('concerns', ['To be monitored'])[0] if pr_analysis.get('concerns') else 'None identified'}

## Alternatives Considered

{chr(10).join('- ' + alt for alt in pr_analysis.get('alternatives', ['No alternatives documented']))}

---
*This ADR was automatically generated from PR discussions and commit analysis.*
"""
        return doc
    
    def generate_onboarding_doc(self, analysis: Dict[str, Any]) -> str:
        """Generate onboarding documentation"""
        doc = f"""# Getting Started Guide
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Welcome to the Project!

This is a {analysis.get('language', 'software')} project with the following structure:

## Project Structure

- **{len(analysis.get('modules', []))} modules**
- **{len(analysis.get('apis', []))} API endpoints**
- **{len(analysis.get('classes', []))} classes**

## Key Entry Points

"""
        
        # Find main entry points
        entry_points = []
        for module in analysis.get('modules', []):
            if 'main' in module['name'].lower() or 'app' in module['name'].lower():
                entry_points.append(module)
        
        for ep in entry_points[:3]:
            doc += f"- `{ep['path']}` - {ep['name']}\n"
        
        doc += "\n## Important Modules\n\n"
        
        for module in analysis.get('modules', [])[:5]:
            doc += f"### {module['name']}\n"
            doc += f"Location: `{module['path']}`\n\n"
        
        doc += """
## Next Steps

1. Clone the repository
2. Install dependencies
3. Review the architecture documentation
4. Check the API documentation for available endpoints
5. Run tests to ensure everything works

## Need Help?

Check the architecture docs or reach out to the team!
"""
        return doc
