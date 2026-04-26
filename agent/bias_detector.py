"""
Bias Detection Module
Analyzes job descriptions for potentially biased or exclusionary language.
Promotes fair hiring practices and wider talent pool access.
"""

from typing import Dict, List


class BiasDetector:
    """
    Scans JD text and parsed requirements for bias signals.
    Categories: gendered language, age bias, unnecessary requirements, exclusionary terms.
    """

    GENDERED_TERMS = {
        "he ": "they", "him ": "them", "his ": "their",
        "manpower": "workforce", "chairman": "chairperson",
        "manmade": "synthetic", "mankind": "humankind",
        "guys": "team", "rockstar": "high-performer",
        "ninja": "expert", "guru": "specialist",
        "aggressive": "driven", "dominant": "leading",
        "hacker": "developer", "brotherhood": "community",
    }

    AGE_BIAS_TERMS = [
        "young", "energetic", "fresh graduate only", "digital native",
        "recent graduate", "gen z", "millennial", "young blood",
        "junior only", "not more than", "maximum age", "age limit",
    ]

    EXCLUSIONARY_TERMS = [
        "native english speaker", "mother tongue",
        "physically fit", "no disabilities",
        "married", "unmarried", "single",
        "specific religion", "specific caste",
    ]

    UNNECESSARY_REQUIREMENTS = {
        "degree required": "Consider skills-based hiring — many top engineers are self-taught",
        "iit": "Restricting to specific institutions limits talent pool significantly",
        "nit": "Restricting to specific institutions limits talent pool significantly",
        "tier 1 college": "Tier-based filtering excludes qualified candidates from diverse backgrounds",
        "tier-1": "Tier-based filtering excludes qualified candidates from diverse backgrounds",
        "10+ years": "Consider if this experience level is truly necessary for the role",
        "15+ years": "Consider if this experience level is truly necessary for the role",
    }

    def analyze_jd(self, jd_text: str, jd_parsed: Dict) -> Dict:
        """
        Analyze JD for bias and return structured report.
        """
        text_lower = jd_text.lower()
        issues = []
        suggestions = []

        # 1. Gendered language check
        for term, replacement in self.GENDERED_TERMS.items():
            if term in text_lower:
                issues.append({
                    "type": "gendered_language",
                    "term": term.strip(),
                    "severity": "medium",
                    "suggestion": f"Consider using '{replacement}' instead of '{term.strip()}'"
                })

        # 2. Age bias check
        for term in self.AGE_BIAS_TERMS:
            if term in text_lower:
                issues.append({
                    "type": "age_bias",
                    "term": term,
                    "severity": "high",
                    "suggestion": f"Remove age-related term '{term}' — focus on skills and experience instead"
                })

        # 3. Exclusionary language check
        for term in self.EXCLUSIONARY_TERMS:
            if term in text_lower:
                issues.append({
                    "type": "exclusionary",
                    "term": term,
                    "severity": "high",
                    "suggestion": f"Remove exclusionary term '{term}' — may violate equal opportunity guidelines"
                })

        # 4. Unnecessary requirement inflation
        for term, suggestion in self.UNNECESSARY_REQUIREMENTS.items():
            if term in text_lower:
                issues.append({
                    "type": "requirement_inflation",
                    "term": term,
                    "severity": "low",
                    "suggestion": suggestion
                })

        # 5. Experience range analysis
        exp = jd_parsed.get("experience_years", {})
        exp_min = exp.get("min") or 0
        exp_max = exp.get("max") or 10
        if exp_max - exp_min < 2 and exp_min > 0:
            suggestions.append("Very narrow experience range may exclude qualified candidates. Consider widening by 1-2 years.")

        # 6. Salary range analysis
        sal = jd_parsed.get("salary_range_lpa", {})
        sal_min = sal.get("min") or 0
        sal_max = sal.get("max") or 0
        if sal_max > 0 and sal_min > 0:
            if (sal_max - sal_min) / sal_max < 0.2:
                suggestions.append("Narrow salary band may limit negotiation flexibility and reduce applicant pool.")

        # 7. Skill count analysis
        req_skills = jd_parsed.get("required_skills", [])
        if len(req_skills) > 8:
            suggestions.append(f"JD lists {len(req_skills)} required skills — consider splitting into 'required' (3-5) and 'nice-to-have'. Long requirement lists deter qualified candidates.")

        # Build report
        issue_types = list(set(i["type"] for i in issues))
        
        return {
            "issues_found": len(issues),
            "issues": issues,
            "issue_types": issue_types,
            "suggestions": suggestions,
            "fairness_score": max(0, 100 - len(issues) * 15 - len(suggestions) * 5),
            "summary": self._generate_summary(issues, suggestions)
        }

    def _generate_summary(self, issues: List[Dict], suggestions: List[str]) -> str:
        if not issues and not suggestions:
            return "✅ No significant bias detected. JD appears inclusive and well-structured."
        
        parts = []
        if issues:
            high = [i for i in issues if i["severity"] == "high"]
            medium = [i for i in issues if i["severity"] == "medium"]
            if high:
                parts.append(f"🔴 {len(high)} high-severity bias issue(s) found")
            if medium:
                parts.append(f"🟡 {len(medium)} medium-severity language issue(s)")
        if suggestions:
            parts.append(f"💡 {len(suggestions)} improvement suggestion(s)")
        
        return " | ".join(parts)
