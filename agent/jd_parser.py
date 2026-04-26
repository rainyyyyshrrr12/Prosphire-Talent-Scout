"""
Step 1: Parse Job Description into structured requirements.
Uses LLM for intelligent extraction + keyword fallback.
"""

import json
from typing import Dict, List
from agent.llm_engine import FreeLLMEngine


class JDParser:
    def __init__(self):
        self.llm = FreeLLMEngine()
    
    def parse(self, jd_text: str) -> Dict:
        """
        Parse JD into structured format using LLM.
        Returns dict with: title, location, required_skills, experience_years,
        salary_range_lpa, key_responsibilities, nice_to_have
        """
        
        system_prompt = """You are an expert recruiter AI. Parse the job description into a structured JSON format.
        Extract all relevant information accurately. Return ONLY valid JSON, no markdown formatting."""

        user_prompt = f"""Parse this job description and return JSON with this exact structure:
{{
    "title": "job title",
    "location": "location or 'Remote'",
    "required_skills": ["skill1", "skill2"],
    "experience_years": {{"min": 2, "max": 5, "exact": null}},
    "salary_range_lpa": {{"min": 10, "max": 20}},
    "key_responsibilities": ["responsibility 1", "responsibility 2"],
    "nice_to_have": ["skill1", "skill2"],
    "education_required": "degree requirement or 'Any'",
    "notice_preference_days": 30
}}

Job Description:
{jd_text}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.llm.generate(messages, temperature=0.2)
        
        # Extract JSON from response (handle markdown wrapping)
        try:
            # Try to find JSON in the response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                parsed = json.loads(json_str)
            else:
                parsed = json.loads(response)
            
            # Add raw text for reference
            parsed["raw_text"] = jd_text
            
            # Normalize skills to lowercase for matching
            parsed["required_skills_lower"] = [s.lower() for s in parsed.get("required_skills", [])]
            parsed["nice_to_have_lower"] = [s.lower() for s in parsed.get("nice_to_have", [])]
            
            return parsed
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse LLM response as JSON: {e}")
            print(f"Response was: {response[:500]}")
            # Return basic structure as fallback
            return {
                "title": "Unknown",
                "location": "Any",
                "required_skills": [],
                "experience_years": {"min": 0, "max": 10, "exact": None},
                "salary_range_lpa": {"min": 0, "max": 100},
                "key_responsibilities": [],
                "nice_to_have": [],
                "education_required": "Any",
                "notice_preference_days": 60,
                "raw_text": jd_text,
                "required_skills_lower": [],
                "nice_to_have_lower": []
            }