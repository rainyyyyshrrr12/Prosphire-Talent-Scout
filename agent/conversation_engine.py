"""
Multi-Turn Conversation Engine
Simulates realistic 6-turn recruiter-candidate dialogue with persona-based responses.
"""

import json
from typing import List, Dict
from dataclasses import dataclass
from agent.llm_engine import FreeLLMEngine


@dataclass
class ConversationTurn:
    turn_number: int
    speaker: str  # "recruiter" or "candidate"
    message: str
    intent: str  # e.g., "intro", "interest_probe", "negotiation"


class ConversationEngine:
    """
    Generates realistic 6-turn recruiter-candidate conversations.
    Structure: Intro → Response → Deep-dive → Probe concerns → Negotiation → Final stance
    
    Uses candidate persona generation for realistic, differentiated responses.
    """

    def __init__(self):
        self.llm = FreeLLMEngine()

    def generate_conversation(self, candidate: Dict, jd: Dict) -> List[ConversationTurn]:
        """
        Generate a 6-turn conversation with persona-based realistic dynamics.
        """
        conversation = []
        context = self._build_context(candidate, jd)
        persona = self._generate_persona(candidate, jd)

        # Turn structure with intents
        turns = [
            (1, "recruiter", "intro",
             "Introduce the role briefly. Mention 2 key requirements that match the candidate's profile. Be personalized — reference their current role. Keep it under 50 words."),
            (2, "candidate", "initial_response",
             f"Respond based on this persona: {persona}. React to the role introduction. Mention 1 specific thing about the role that catches your attention. Under 50 words."),
            (3, "recruiter", "deep_dive",
             "Ask a specific technical question about their experience with a key required skill. Show genuine interest in their background. Under 40 words."),
            (4, "candidate", "technical_response",
             f"Persona: {persona}. Answer the technical question with a concrete example from your experience. Show depth of knowledge. Under 60 words."),
            (5, "recruiter", "availability_probe",
             "Ask about their notice period, salary expectations, and what would make this the right move for them. Under 40 words."),
            (6, "candidate", "commitment_signal",
             f"Persona: {persona}. Give your final response about availability and interest. Be realistic — if the role is great, show enthusiasm. If there are concerns (salary, location, notice), mention them diplomatically. Under 60 words.")
        ]

        try:
            for turn_num, speaker, intent, prompt in turns:
                if speaker == "recruiter":
                    msg = self._generate_recruiter_message(context, conversation, prompt)
                else:
                    msg = self._generate_candidate_response(context, conversation, prompt)
                conversation.append(ConversationTurn(turn_num, speaker, msg, intent))
        except Exception as e:
            print(f"Conversation LLM fallback used for {candidate.get('name', 'candidate')}: {e}")
            return self._generate_fallback_conversation(candidate, jd)

        return conversation

    def _generate_persona(self, candidate: Dict, jd: Dict) -> str:
        """Generate a brief candidate persona for consistent conversation behavior."""
        salary_match = candidate.get("salary_expectation_lpa", 0) <= jd.get("salary_range_lpa", {}).get("max", 100)
        exp_years = candidate.get("experience_years", 0)
        notice = candidate.get("notice_period_days", 60)

        # Determine enthusiasm level based on fit signals
        jd_skills = set(s.lower() for s in jd.get("required_skills", []))
        cand_skills = set(s.lower() for s in candidate.get("skills", []))
        skill_overlap = len(jd_skills & cand_skills) / max(len(jd_skills), 1)

        if skill_overlap > 0.5 and salary_match:
            tone = "enthusiastic and engaged — this role aligns well with their career goals"
        elif skill_overlap > 0.3:
            tone = "curious but cautious — interested but has some questions about fit"
        else:
            tone = "polite but non-committal — open to hearing more but not actively looking"

        return (
            f"{candidate['name']} is a {candidate['current_role']} with {exp_years} years experience. "
            f"They are {tone}. Notice period: {notice} days. "
            f"Salary expectation: ₹{candidate.get('salary_expectation_lpa', 0)} LPA. "
            f"{'Salary is within budget.' if salary_match else 'Salary expectation exceeds budget — may raise this concern.'}"
        )

    def _build_context(self, candidate: Dict, jd: Dict) -> str:
        return f"""JOB: {jd.get('title', 'Unknown')} at {jd.get('location', 'Any')}
Salary: ₹{jd.get('salary_range_lpa', {}).get('min', 0)}-{jd.get('salary_range_lpa', {}).get('max', 0)} LPA
Required Skills: {', '.join(jd.get('required_skills', []))}

CANDIDATE: {candidate['name']}
Current: {candidate['current_role']} ({candidate['experience_years']} yrs)
Skills: {', '.join(candidate['skills'])}
Location: {candidate['location']}
Salary Expectation: ₹{candidate['salary_expectation_lpa']} LPA
Notice: {candidate['notice_period_days']} days
Bio: {candidate['bio']}"""

    def _generate_fallback_conversation(self, candidate: Dict, jd: Dict) -> List[ConversationTurn]:
        """Generate a deterministic conversation when all LLM providers fail."""
        name = candidate.get("name", "the candidate")
        role = candidate.get("current_role", "professional")
        job_title = jd.get("title", "the role")
        location = jd.get("location", "the listed location")
        required_skills = jd.get("required_skills", [])
        candidate_skills = candidate.get("skills", [])
        salary_max = jd.get("salary_range_lpa", {}).get("max") or 0
        salary_expectation = candidate.get("salary_expectation_lpa", 0)
        notice = candidate.get("notice_period_days", 30)

        matched_skills = [
            skill for skill in candidate_skills
            if skill.lower() in {s.lower() for s in required_skills}
        ]
        primary_skill = matched_skills[0] if matched_skills else (candidate_skills[0] if candidate_skills else "the required stack")
        salary_text = (
            "The salary range looks aligned with my expectations."
            if salary_max and salary_expectation <= salary_max
            else "I would want to discuss the compensation range in more detail."
        )
        interest_text = (
            "I am very interested because the role matches my recent work."
            if matched_skills
            else "I am open to learning more, though I would want to understand the fit better."
        )

        return [
            ConversationTurn(
                1,
                "recruiter",
                f"Hi {name}, your background as a {role} looks relevant for our {job_title} role, especially around {primary_skill}. Would you be open to a quick discussion?",
                "intro",
            ),
            ConversationTurn(
                2,
                "candidate",
                f"Thanks for reaching out. {interest_text} The {job_title} opportunity sounds worth exploring.",
                "initial_response",
            ),
            ConversationTurn(
                3,
                "recruiter",
                f"Great. Could you share a recent example of how you used {primary_skill} in a project?",
                "deep_dive",
            ),
            ConversationTurn(
                4,
                "candidate",
                f"I have used {primary_skill} in production work and can walk through the architecture, tradeoffs, and outcomes in an interview.",
                "technical_response",
            ),
            ConversationTurn(
                5,
                "recruiter",
                f"What is your notice period, salary expectation, and comfort with the role location: {location}?",
                "availability_probe",
            ),
            ConversationTurn(
                6,
                "candidate",
                f"My notice period is around {notice} days. {salary_text} I am open to the next step if the team, scope, and offer are aligned.",
                "commitment_signal",
            ),
        ]

    def _generate_recruiter_message(self, context: str, history: List[ConversationTurn], prompt: str) -> str:
        hist_text = "\n".join(
            f"{'Recruiter' if t.speaker == 'recruiter' else 'Candidate'}: {t.message}"
            for t in history
        )

        system = f"""You are a professional tech recruiter. You are reaching out to a candidate about a role.
{context}

{'Previous conversation:\\n' + hist_text if hist_text else ''}

Generate ONLY the recruiter's message. No labels, no quotes, just the message text."""

        response = self.llm.generate([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ], temperature=0.7)

        return response.strip().strip('"').strip("'")

    def _generate_candidate_response(self, context: str, history: List[ConversationTurn], prompt: str) -> str:
        hist_text = "\n".join(
            f"{'Recruiter' if t.speaker == 'recruiter' else 'Candidate'}: {t.message}"
            for t in history
        )

        system = f"""You are roleplaying as the candidate described below. Respond naturally, realistically.
{context}

Previous conversation:
{hist_text}

Generate ONLY the candidate's next response. No labels, no quotes, just the message text."""

        response = self.llm.generate([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ], temperature=0.8)

        return response.strip().strip('"').strip("'")
