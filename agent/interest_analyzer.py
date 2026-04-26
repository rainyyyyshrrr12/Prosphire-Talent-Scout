"""
Interest Analyzer
Derives Interest Score from conversation signals, not self-reporting.
"""

import re
from typing import List, Dict
from dataclasses import dataclass
from agent.conversation_engine import ConversationTurn


@dataclass
class InterestSignals:
    candidate_id: str = ""
    candidate_name: str = ""
    enthusiasm_score: float = 0.0
    engagement_score: float = 0.0
    commitment_score: float = 0.0
    total_interest_score: float = 0.0
    positive_signals: List[str] = None
    negative_signals: List[str] = None
    questions_asked: int = 0
    availability_commitment: str = ""

    def __post_init__(self):
        if self.positive_signals is None:
            self.positive_signals = []
        if self.negative_signals is None:
            self.negative_signals = []


class InterestAnalyzer:
    """
    Analyzes conversation transcript for genuine interest signals.
    Methodology is transparent and defensible.
    """
    
    # Signal dictionaries
    ENTHUSIASM_POSITIVE = [
        "excited", "thrilled", "perfect fit", "ideal", "love to", "definitely interested",
        "sounds great", "amazing opportunity", "exactly what", "passionate about",
        "very interested", "keen to", "would love", "absolutely", "count me in",
        "strong match", "aligned with", "eager to"
    ]
    
    ENTHUSIASM_NEGATIVE = [
        "not sure", "maybe", "need to think", "hesitant", "not the right time",
        "comfortable where i am", "not looking", "happy current", "reluctant",
        "skeptical", "concerned about", "worried", "doesn't seem", "too risky"
    ]
    
    ENGAGEMENT_MARKERS = [
        "what about", "how does", "can you tell me", "what is the", "who would",
        "what team", "tech stack", "culture", "growth", "learning", "challenge"
    ]
    
    COMMITMENT_POSITIVE = [
        "can join", "available in", "notice period is", "can start",
        "flexible on", "willing to", "open to", "ready to move"
    ]
    
    COMMITMENT_NEGATIVE = [
        "locked in", "contract until", "cannot leave", "bond", "committed to current",
        "just started", "too early", "not possible", "stuck"
    ]
    
    def analyze(self, conversation: List[ConversationTurn], candidate: Dict) -> InterestSignals:
        """
        Analyze conversation for interest signals using weighted scoring.
        """
        
        all_text = " ".join([t.message.lower() for t in conversation])
        candidate_text = " ".join([t.message.lower() for t in conversation if t.speaker == "candidate"])
        
        positive_signals = []
        negative_signals = []
        
        # 1. Enthusiasm Analysis (0-40 points)
        enthusiasm = 20.0  # Baseline neutral
        
        for word in self.ENTHUSIASM_POSITIVE:
            if word in candidate_text:
                enthusiasm += 4
                positive_signals.append(f"Enthusiasm marker: '{word}'")
        
        for word in self.ENTHUSIASM_NEGATIVE:
            if word in candidate_text:
                enthusiasm -= 6
                negative_signals.append(f"Hesitation marker: '{word}'")
        
        # Profile-fit bonus (if candidate mentions their skills matching)
        cand_skills = [s.lower() for s in candidate.get("skills", [])]
        for skill in cand_skills:
            if skill in all_text and any(t.speaker == "candidate" for t in conversation if skill in t.message.lower()):
                enthusiasm += 2
                positive_signals.append(f"Self-identified skill fit: {skill}")
        
        enthusiasm = max(0, min(40, enthusiasm))
        
        # 2. Engagement Analysis (0-30 points)
        engagement = 10.0  # Baseline
        
        # Count questions asked by candidate
        questions = len(re.findall(r'\?', candidate_text))
        engagement += questions * 5
        if questions >= 2:
            positive_signals.append(f"Asked {questions} questions (high engagement)")
        
        for marker in self.ENGAGEMENT_MARKERS:
            if marker in candidate_text:
                engagement += 3
                positive_signals.append(f"Engagement marker: '{marker}'")
        
        # Response length (engaged candidates write more)
        avg_response_len = sum(len(t.message) for t in conversation if t.speaker == "candidate") / max(1, sum(1 for t in conversation if t.speaker == "candidate"))
        if avg_response_len > 80:
            engagement += 3
            positive_signals.append("Detailed responses (high engagement)")
        elif avg_response_len < 30:
            engagement -= 5
            negative_signals.append("Very short responses (low engagement)")
        
        engagement = max(0, min(30, engagement))
        
        # 3. Commitment Analysis (0-30 points)
        commitment = 15.0  # Baseline
        
        for word in self.COMMITMENT_POSITIVE:
            if word in candidate_text:
                commitment += 5
                positive_signals.append(f"Commitment signal: '{word}'")
        
        for word in self.COMMITMENT_NEGATIVE:
            if word in candidate_text:
                commitment -= 8
                negative_signals.append(f"Commitment blocker: '{word}'")
        
        # Notice period alignment
        notice = candidate.get("notice_period_days", 60)
        if notice <= 30:
            commitment += 5
            positive_signals.append("Short notice period (highly available)")
        elif notice >= 90:
            commitment -= 3
            negative_signals.append("Long notice period (3+ months)")
        
        commitment = max(0, min(30, commitment))
        
        # Total
        total = enthusiasm + engagement + commitment
        
        # Determine availability commitment text
        if commitment >= 22:
            avail = "High commitment — likely to join if offer matches"
        elif commitment >= 15:
            avail = "Moderate commitment — needs convincing on role fit"
        elif commitment >= 8:
            avail = "Low commitment — exploring options passively"
        else:
            avail = "Very low commitment — unlikely to move"
        
        return InterestSignals(
            enthusiasm_score=round(enthusiasm, 1),
            engagement_score=round(engagement, 1),
            commitment_score=round(commitment, 1),
            total_interest_score=round(total, 1),
            positive_signals=list(set(positive_signals)),
            negative_signals=list(set(negative_signals)),
            questions_asked=questions,
            availability_commitment=avail
        )