import re
from typing import List, Dict, Any
import anthropic

class NLPProcessor:
    """Process natural language from commits, PRs, and communications"""
    
    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
    
    def extract_intent(self, commit_message: str) -> Dict[str, Any]:
        """Extract intent and categories from commit message"""
        message_lower = commit_message.lower()
        
        # Pattern matching for common intents
        intent = {
            "type": "other",
            "action": None,
            "component": None,
            "reason": None
        }
        
        # Detect type
        if any(word in message_lower for word in ["fix", "bug", "issue", "error"]):
            intent["type"] = "bugfix"
        elif any(word in message_lower for word in ["feat", "feature", "add", "new"]):
            intent["type"] = "feature"
        elif any(word in message_lower for word in ["refactor", "cleanup", "restructure"]):
            intent["type"] = "refactor"
        elif any(word in message_lower for word in ["doc", "documentation", "readme"]):
            intent["type"] = "documentation"
        
        # Extract action verbs
        action_verbs = ["add", "remove", "update", "fix", "refactor", "implement", "create"]
        for verb in action_verbs:
            if verb in message_lower:
                intent["action"] = verb
                break
        
        return intent
    
    def analyze_pr_discussion(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze PR description and comments for decisions"""
        if not self.client:
            return {"decisions": [], "concerns": [], "alternatives": []}
        
        # Combine PR title, description, and comments
        text = f"Title: {pr_data.get('title', '')}\n"
        text += f"Description: {pr_data.get('body', '')}\n"
        
        for comment in pr_data.get('comments', []):
            text += f"Comment: {comment.get('body', '')}\n"
        
        # Use Claude to extract structured information
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze this PR discussion and extract:
1. Key decisions made
2. Technical concerns raised
3. Alternative approaches discussed
4. Rationale for the chosen approach

PR Discussion:
{text[:4000]}

Respond in JSON format with keys: decisions, concerns, alternatives, rationale"""
                }]
            )
            
            # Parse response (simplified - add proper JSON parsing)
            response_text = message.content[0].text
            return {
                "decisions": [],
                "concerns": [],
                "alternatives": [],
                "rationale": response_text
            }
        except Exception as e:
            print(f"NLP analysis error: {e}")
            return {"decisions": [], "concerns": [], "alternatives": []}
    
    def extract_decisions(self, slack_messages: List[Dict]) -> List[Dict[str, Any]]:
        """Extract architectural decisions from Slack conversations"""
        decisions = []
        
        # Look for decision keywords
        decision_keywords = [
            "we decided", "decision", "let's use", "we'll go with",
            "agreed to", "consensus", "we should"
        ]
        
        for msg in slack_messages:
            text = msg.get("text", "").lower()
            
            for keyword in decision_keywords:
                if keyword in text:
                    decisions.append({
                        "text": msg.get("text"),
                        "author": msg.get("user"),
                        "timestamp": msg.get("ts"),
                        "context": "slack",
                        "confidence": 0.7
                    })
                    break
        
        return decisions
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate concise summary of text"""
        if not self.client:
            # Fallback: simple truncation
            return text[:max_length] + "..." if len(text) > max_length else text
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_length,
                messages=[{
                    "role": "user",
                    "content": f"Summarize this in one paragraph:\n\n{text[:2000]}"
                }]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Summary generation error: {e}")
            return text[:max_length]