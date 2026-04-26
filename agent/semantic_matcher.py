"""
Semantic Matching Module
Handles skill synonym resolution and fuzzy matching.
"""

from typing import List, Set, Dict
from difflib import SequenceMatcher


class SemanticSkillMatcher:
    """
    Matches skills beyond exact keyword overlap.
    Handles: React.js ≈ ReactJS ≈ React, Python ≈ Python3, etc.
    """
    
    # Built-in synonym map for common tech skills
    SYNONYMS = {
        "react": ["reactjs", "react.js", "react (frontend framework)"],
        "reactjs": ["react", "react.js"],
        "react.js": ["react", "reactjs"],
        "python": ["python3", "py"],
        "python3": ["python", "py"],
        "node": ["nodejs", "node.js"],
        "nodejs": ["node", "node.js"],
        "node.js": ["node", "nodejs"],
        "aws": ["amazon web services", "ec2", "s3", "amazon cloud"],
        "gcp": ["google cloud platform", "google cloud"],
        "azure": ["microsoft azure"],
        "postgres": ["postgresql"],
        "postgresql": ["postgres"],
        "js": ["javascript"],
        "javascript": ["js"],
        "ts": ["typescript"],
        "typescript": ["ts"],
        "k8s": ["kubernetes"],
        "kubernetes": ["k8s"],
        "ml": ["machine learning"],
        "machine learning": ["ml"],
        "ai": ["artificial intelligence"],
        "artificial intelligence": ["ai"],
        "nlp": ["natural language processing"],
        "natural language processing": ["nlp"],
        "ci/cd": ["cicd", "continuous integration", "continuous deployment"],
        "rest": ["restful", "rest api", "rest apis"],
        "restful": ["rest", "rest api"],
    }
    
    @classmethod
    def normalize_skill(cls, skill: str) -> str:
        """Normalize skill name to canonical form."""
        s = skill.lower().strip().replace(".", "").replace(" ", "")
        return cls.SYNONYMS.get(s, [s])[0] if s in cls.SYNONYMS else s
    
    @classmethod
    def expand_skills(cls, skills: List[str]) -> Set[str]:
        """Expand skill list to include synonyms."""
        expanded = set()
        for skill in skills:
            s_lower = skill.lower().strip()
            expanded.add(s_lower)
            # Add synonyms
            for canonical, synonyms in cls.SYNONYMS.items():
                if s_lower == canonical or s_lower in synonyms:
                    expanded.add(canonical)
                    expanded.update(synonyms)
        return expanded
    
    @classmethod
    def fuzzy_match_score(cls, skill1: str, skill2: str) -> float:
        """Return similarity ratio between two skill strings."""
        return SequenceMatcher(None, skill1.lower(), skill2.lower()).ratio()
    
    @classmethod
    def calculate_semantic_overlap(cls, jd_skills: List[str], cand_skills: List[str]) -> Dict:
        """
        Calculate skill overlap with synonym resolution.
        Returns detailed breakdown.
        """
        jd_expanded = cls.expand_skills(jd_skills)
        cand_expanded = cls.expand_skills(cand_skills)
        
        # Direct matches (including synonyms)
        direct_matches = jd_expanded & cand_expanded
        
        # Fuzzy matches for remaining
        jd_remaining = jd_expanded - direct_matches
        cand_remaining = cand_expanded - direct_matches
        
        fuzzy_matches = []
        for js in jd_remaining:
            for cs in cand_remaining:
                if cls.fuzzy_match_score(js, cs) >= 0.85:
                    fuzzy_matches.append((js, cs))
        
        total_jd = len(jd_expanded) if jd_expanded else 1
        
        return {
            "direct_matches": list(direct_matches),
            "fuzzy_matches": fuzzy_matches,
            "total_jd_skills": len(jd_expanded),
            "matched_count": len(direct_matches) + len(fuzzy_matches),
            "match_percentage": round((len(direct_matches) + len(fuzzy_matches)) / total_jd * 100, 1),
            "unmatched_jd_skills": list(jd_remaining - set(m[0] for m in fuzzy_matches))
        }