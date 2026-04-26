"""
Step 2: Match candidates to JD requirements.
Produces Match Score (0-100) with full explainability.
"""

import json
from typing import Dict, List
from dataclasses import dataclass
from agent.semantic_matcher import SemanticSkillMatcher


@dataclass
class MatchResult:
    candidate_id: str
    candidate_name: str
    match_score: float
    skill_match_score: float
    experience_match_score: float
    salary_match_score: float
    location_match_score: float
    overall_explanation: str
    skill_breakdown: Dict
    raw_candidate: Dict
    factor_breakdown: Dict  # NEW: Per-factor tree for explainability


class CandidateMatcher:
    """
    Deep candidate matcher with multi-factor scoring and explainability.
    Candidates are passed as parameters — no file I/O needed.
    """
    def __init__(self):
        pass
    
    def calculate_match(self, jd: Dict, candidate: Dict) -> MatchResult:
        """
        Calculate comprehensive match score with full explainability.
        """
        
        # 1. Skill Match (40% weight) — NOW WITH SEMANTIC MATCHING
        semantic = SemanticSkillMatcher.calculate_semantic_overlap(
            jd.get("required_skills", []) + jd.get("nice_to_have", []),
            candidate.get("skills", [])
        )
        
        skill_score = semantic["match_percentage"] * 0.4  # Scale to 40 points
        
        skill_breakdown = {
            "required_skills": jd.get("required_skills", []),
            "candidate_skills": candidate.get("skills", []),
            "matched_skills": semantic["direct_matches"] + [f"{m[0]}≈{m[1]}" for m in semantic["fuzzy_matches"]],
            "missing_skills": semantic["unmatched_jd_skills"],
            "semantic_match_pct": semantic["match_percentage"],
            "fuzzy_matches_found": len(semantic["fuzzy_matches"])
        }
        
        # 2. Experience Match (25% weight)
        exp_req = jd.get("experience_years", {})
        cand_exp = candidate.get("experience_years", 0)
        
        if exp_req.get("exact"):
            target = exp_req["exact"]
            if cand_exp == target:
                exp_score = 25.0
                exp_note = f"Exact match: {cand_exp} years"
            else:
                diff = abs(cand_exp - target)
                exp_score = max(0, 25 - diff * 5)
                exp_note = f"{cand_exp} yrs vs required {target} yrs (diff: {diff})"
        else:
            min_exp = exp_req.get("min") or 0
            max_exp = exp_req.get("max") or 10
            
            if min_exp <= cand_exp <= max_exp:
                mid = (min_exp + max_exp) / 2
                diff = abs(cand_exp - mid)
                exp_score = 25 - (diff / (max_exp - min_exp + 1)) * 5
                exp_note = f"{cand_exp} yrs — within range {min_exp}-{max_exp}"
            elif cand_exp < min_exp:
                gap = min_exp - cand_exp
                exp_score = max(0, 25 - gap * 4)
                exp_note = f"{cand_exp} yrs — {gap} yrs below minimum"
            else:
                over = cand_exp - max_exp
                exp_score = max(15, 25 - over * 2)
                exp_note = f"{cand_exp} yrs — {over} yrs above range (overqualified)"
        
        # 3. Salary Match (20% weight)
        salary_range = jd.get("salary_range_lpa", {})
        cand_salary = candidate.get("salary_expectation_lpa", 0)
        min_sal = salary_range.get("min", 0)
        max_sal = salary_range.get("max", 100)
        
        if min_sal <= cand_salary <= max_sal:
            sal_score = 20.0
            sal_note = f"₹{cand_salary} LPA within budget ₹{min_sal}-{max_sal} LPA"
        elif cand_salary < min_sal:
            sal_score = 18.0
            sal_note = f"₹{cand_salary} LPA — under budget (good for company)"
        else:
            over_pct = (cand_salary - max_sal) / max_sal if max_sal > 0 else 1
            sal_score = max(0, 20 - over_pct * 20)
            sal_note = f"₹{cand_salary} LPA — {(over_pct*100):.0f}% over max budget"
        
        # 4. Location Match (15% weight)
        jd_location = jd.get("location", "Any").lower()
        cand_location = candidate.get("location", "").lower()
        
        if "remote" in jd_location or "any" in jd_location:
            loc_score = 15.0
            loc_note = "Remote/Any location — full points"
        elif jd_location in cand_location or cand_location in jd_location:
            loc_score = 15.0
            loc_note = f"Exact location match: {candidate['location']}"
        else:
            loc_score = 6.0
            loc_note = f"{candidate['location']} vs {jd.get('location')} — different city, assume open to relocate"
        
        # Final score
        final_score = skill_score + exp_score + sal_score + loc_score
        
        # Explainability tree
        factor_breakdown = {
            "skills": {
                "score": round(skill_score, 1),
                "max": 40,
                "percentage": round((skill_score / 40) * 100, 1),
                "note": f"{len(skill_breakdown['matched_skills'])} matched, {len(skill_breakdown['missing_skills'])} missing"
            },
            "experience": {
                "score": round(exp_score, 1),
                "max": 25,
                "percentage": round((exp_score / 25) * 100, 1),
                "note": exp_note
            },
            "salary": {
                "score": round(sal_score, 1),
                "max": 20,
                "percentage": round((sal_score / 20) * 100, 1),
                "note": sal_note
            },
            "location": {
                "score": round(loc_score, 1),
                "max": 15,
                "percentage": round((loc_score / 15) * 100, 1),
                "note": loc_note
            }
        }
        
        explanation = self._generate_explanation(candidate, factor_breakdown, skill_breakdown)
        
        return MatchResult(
            candidate_id=candidate["id"],
            candidate_name=candidate["name"],
            match_score=round(final_score, 1),
            skill_match_score=round(skill_score, 1),
            experience_match_score=round(exp_score, 1),
            salary_match_score=round(sal_score, 1),
            location_match_score=round(loc_score, 1),
            overall_explanation=explanation,
            skill_breakdown=skill_breakdown,
            raw_candidate=candidate,
            factor_breakdown=factor_breakdown
        )
    
    def _generate_explanation(self, candidate, factors, breakdown) -> str:
        parts = [
            f"Skills {factors['skills']['score']:.0f}/40 — {factors['skills']['note']}",
            f"Experience {factors['experience']['score']:.0f}/25 — {factors['experience']['note']}",
            f"Salary {factors['salary']['score']:.0f}/20 — {factors['salary']['note']}",
            f"Location {factors['location']['score']:.0f}/15 — {factors['location']['note']}"
        ]
        return " | ".join(parts)
    
    def find_matches(self, jd: Dict, candidate_pool: List[Dict], min_score: float = 50.0, top_k: int = 10) -> List[MatchResult]:
        """Find all candidates above threshold, sorted by match score."""
        results = []
        
        for candidate in candidate_pool:
            match = self.calculate_match(jd, candidate)
            if match.match_score >= min_score:
                results.append(match)
        
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results[:top_k]