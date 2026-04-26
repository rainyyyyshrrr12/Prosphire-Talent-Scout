"""
Market Intelligence Module
Provides recruiter context: salary benchmarks, hiring difficulty, talent supply.
Uses structured heuristics + optional LLM enrichment.
"""

from typing import Dict


class MarketIntelligence:
    """
    Generates market context for a given role based on parsed JD.
    Helps recruiters understand if their JD is competitive.
    """

    # Industry salary benchmarks (LPA) by role category — India market
    SALARY_BENCHMARKS = {
        "ai": {"junior": (8, 15), "mid": (15, 28), "senior": (25, 45), "lead": (35, 60)},
        "ml": {"junior": (8, 15), "mid": (15, 28), "senior": (25, 45), "lead": (35, 60)},
        "backend": {"junior": (5, 12), "mid": (12, 22), "senior": (20, 35), "lead": (30, 50)},
        "frontend": {"junior": (5, 12), "mid": (10, 20), "senior": (18, 32), "lead": (28, 45)},
        "data": {"junior": (6, 14), "mid": (14, 25), "senior": (22, 40), "lead": (35, 55)},
        "devops": {"junior": (6, 14), "mid": (14, 24), "senior": (22, 38), "lead": (32, 50)},
        "fullstack": {"junior": (5, 12), "mid": (12, 22), "senior": (20, 35), "lead": (30, 50)},
        "product": {"junior": (8, 15), "mid": (15, 28), "senior": (25, 45), "lead": (40, 65)},
        "default": {"junior": (5, 12), "mid": (12, 22), "senior": (20, 35), "lead": (30, 50)},
    }

    # Talent supply indicators by skill
    HIGH_DEMAND_SKILLS = [
        "llm", "langchain", "rag", "ai agents", "vector databases",
        "kubernetes", "mlops", "rust", "go", "blockchain",
        "generative ai", "prompt engineering", "fine-tuning",
    ]

    COMMON_SKILLS = [
        "python", "javascript", "java", "sql", "html", "css",
        "react", "node", "django", "flask", "aws", "docker",
        "git", "rest api", "postgresql", "mongodb",
    ]

    def analyze(self, jd: Dict) -> Dict:
        """Generate market intelligence report for the given JD."""
        
        title = jd.get("title", "").lower()
        skills = [s.lower() for s in jd.get("required_skills", [])]
        sal_range = jd.get("salary_range_lpa", {})
        exp_range = jd.get("experience_years", {})
        location = jd.get("location", "Any")

        # Determine role category
        category = self._categorize_role(title, skills)
        
        # Determine seniority
        seniority = self._determine_seniority(title, exp_range)
        
        # Salary benchmark
        benchmark = self._get_salary_benchmark(category, seniority)
        salary_assessment = self._assess_salary(sal_range, benchmark)
        
        # Talent supply assessment
        supply = self._assess_talent_supply(skills)
        
        # Hiring difficulty
        difficulty = self._assess_hiring_difficulty(skills, sal_range, exp_range, location)
        
        # Recommendations
        recommendations = self._generate_recommendations(
            salary_assessment, supply, difficulty, jd
        )

        return {
            "role_category": category,
            "seniority_level": seniority,
            "salary_benchmark": {
                "market_range": f"₹{benchmark[0]}-{benchmark[1]} LPA",
                "market_median": (benchmark[0] + benchmark[1]) // 2,
                "offered_range": f"₹{sal_range.get('min', 0)}-{sal_range.get('max', 0)} LPA",
                "assessment": salary_assessment,
            },
            "talent_supply": supply,
            "hiring_difficulty": difficulty,
            "estimated_time_to_hire": self._estimate_time(difficulty),
            "recommendations": recommendations,
            "hot_skills_in_jd": [s for s in skills if s in self.HIGH_DEMAND_SKILLS],
            "common_skills_in_jd": [s for s in skills if s in self.COMMON_SKILLS],
        }

    def _categorize_role(self, title: str, skills: list) -> str:
        if any(t in title for t in ["ai", "ml", "machine learning", "artificial"]):
            return "ai"
        if any(t in title for t in ["data scientist", "data engineer", "data analyst"]):
            return "data"
        if any(t in title for t in ["devops", "sre", "platform", "infrastructure"]):
            return "devops"
        if any(t in title for t in ["frontend", "front-end", "ui"]):
            return "frontend"
        if any(t in title for t in ["backend", "back-end", "server"]):
            return "backend"
        if any(t in title for t in ["fullstack", "full-stack", "full stack"]):
            return "fullstack"
        if any(t in title for t in ["product manager", "product owner"]):
            return "product"
        # Fallback: infer from skills
        ai_skills = {"llm", "langchain", "tensorflow", "pytorch", "ml", "ai", "nlp"}
        if len(set(skills) & ai_skills) >= 2:
            return "ai"
        return "default"

    def _determine_seniority(self, title: str, exp_range: Dict) -> str:
        title_l = title.lower()
        if any(t in title_l for t in ["lead", "principal", "staff", "head", "director", "vp"]):
            return "lead"
        if any(t in title_l for t in ["senior", "sr.", "sr "]):
            return "senior"
        if any(t in title_l for t in ["junior", "jr.", "jr ", "intern", "fresher", "entry"]):
            return "junior"
        # Infer from experience
        exp_min = exp_range.get("min") or 0
        if exp_min >= 8:
            return "lead"
        if exp_min >= 4:
            return "senior"
        if exp_min >= 2:
            return "mid"
        return "junior"

    def _get_salary_benchmark(self, category: str, seniority: str) -> tuple:
        benchmarks = self.SALARY_BENCHMARKS.get(category, self.SALARY_BENCHMARKS["default"])
        return benchmarks.get(seniority, benchmarks["mid"])

    def _assess_salary(self, offered: Dict, benchmark: tuple) -> str:
        offered_max = offered.get("max") or 0
        offered_min = offered.get("min") or 0
        
        if offered_max == 0:
            return "Not specified — may deter candidates who value transparency"
        
        bench_mid = (benchmark[0] + benchmark[1]) / 2
        
        if offered_max >= benchmark[1]:
            return "💰 Above market — strong competitive advantage"
        elif offered_max >= bench_mid:
            return "✅ Competitive — within market range"
        elif offered_max >= benchmark[0]:
            return "⚠️ Below market median — may struggle to attract top talent"
        else:
            return "🔴 Below market — high risk of candidate rejection"

    def _assess_talent_supply(self, skills: list) -> str:
        hot_count = sum(1 for s in skills if s in self.HIGH_DEMAND_SKILLS)
        common_count = sum(1 for s in skills if s in self.COMMON_SKILLS)
        
        if hot_count >= 3:
            return "🔴 Scarce — multiple high-demand skills required. Expect longer time-to-hire."
        elif hot_count >= 1:
            return "🟡 Limited — some niche skills required. Moderate talent pool."
        elif common_count >= 3:
            return "🟢 Abundant — mostly common skills. Large talent pool available."
        else:
            return "🟡 Moderate — mixed skill requirements."

    def _assess_hiring_difficulty(self, skills, sal_range, exp_range, location) -> str:
        difficulty_score = 0
        
        # Niche skills increase difficulty
        hot_count = sum(1 for s in skills if s in self.HIGH_DEMAND_SKILLS)
        difficulty_score += hot_count * 15
        
        # Narrow experience range
        exp_min = exp_range.get("min") or 0
        exp_max = exp_range.get("max") or 10
        if exp_max - exp_min < 3:
            difficulty_score += 10
        
        # Below-market salary
        sal_max = sal_range.get("max") or 0
        if sal_max > 0 and sal_max < 15:
            difficulty_score += 20
        
        # Location constraints
        loc = location.lower()
        if "remote" not in loc and "any" not in loc and "hybrid" not in loc:
            difficulty_score += 10
        
        if difficulty_score >= 40:
            return "🔴 Hard — expect 4-8 weeks to fill"
        elif difficulty_score >= 20:
            return "🟡 Moderate — expect 2-4 weeks to fill"
        else:
            return "🟢 Easy — expect 1-2 weeks to fill"

    def _estimate_time(self, difficulty: str) -> str:
        if "Hard" in difficulty:
            return "4-8 weeks"
        elif "Moderate" in difficulty:
            return "2-4 weeks"
        else:
            return "1-2 weeks"

    def _generate_recommendations(self, salary_assessment, supply, difficulty, jd) -> list:
        recs = []
        
        if "Below market" in salary_assessment or "below market" in salary_assessment.lower():
            recs.append("Consider increasing salary range to market median to attract stronger candidates.")
        
        if "Scarce" in supply:
            recs.append("Consider making some niche skills 'nice-to-have' instead of required to widen the funnel.")
        
        if "Hard" in difficulty:
            recs.append("This is a competitive hire. Consider offering remote/hybrid flexibility to expand the talent pool.")
        
        skills = jd.get("required_skills", [])
        if len(skills) > 7:
            recs.append(f"JD has {len(skills)} required skills. Trim to 4-5 core skills to avoid deterring qualified candidates.")
        
        if not jd.get("nice_to_have"):
            recs.append("Add a 'Nice-to-have' section — it helps candidates self-assess and increases application rate.")
        
        loc = jd.get("location", "").lower()
        if "remote" not in loc and "hybrid" not in loc:
            recs.append("Consider adding remote/hybrid option — 68% of tech candidates prefer flexible work arrangements.")
        
        if not recs:
            recs.append("JD looks competitive and well-structured. No major adjustments needed.")
        
        return recs
