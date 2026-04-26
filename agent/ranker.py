"""
Step 4: Combine Match Score and Interest Score into final ranking.
"""

from typing import List, Dict
from dataclasses import dataclass, asdict
from agent.matcher import MatchResult
from agent.interest_analyzer import InterestSignals


@dataclass
class FinalRankedCandidate:
    rank: int
    candidate_id: str
    candidate_name: str
    match_score: float
    interest_score: float
    combined_score: float
    match_explanation: str
    interest_explanation: str
    availability_timeline: str
    concerns: List[str]
    enthusiasm_signals: List[str]
    skill_breakdown: Dict
    factor_breakdown: Dict
    conversation_preview: str
    recommendation: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


class CandidateRanker:
    def rank_candidates(
        self,
        match_results: List[MatchResult],
        interest_signals: List[InterestSignals],
        match_weight: float = 0.6,
        interest_weight: float = 0.4
    ) -> List[FinalRankedCandidate]:
        
        interest_map = {s.candidate_id: s for s in interest_signals}
        
        ranked = []
        
        for match in match_results:
            interest = interest_map.get(match.candidate_id)
            if not interest:
                continue
            
            combined = (match.match_score * match_weight + 
                       interest.total_interest_score * interest_weight)
            
            recommendation = self._generate_recommendation(
                match.match_score, interest.total_interest_score, combined
            )
            
            preview = f"Enthusiasm: {interest.enthusiasm_score}/40 | Engagement: {interest.engagement_score}/30 | Commitment: {interest.commitment_score}/30"
            
            ranked.append(FinalRankedCandidate(
                rank=0,
                candidate_id=match.candidate_id,
                candidate_name=match.candidate_name,
                match_score=match.match_score,
                interest_score=interest.total_interest_score,
                combined_score=round(combined, 1),
                match_explanation=match.overall_explanation,
                interest_explanation=f"{interest.availability_commitment}. {len(interest.positive_signals)} positive signals, {len(interest.negative_signals)} concerns.",
                availability_timeline=interest.availability_commitment,
                concerns=interest.negative_signals,
                enthusiasm_signals=interest.positive_signals,
                skill_breakdown=match.skill_breakdown,
                factor_breakdown=match.factor_breakdown,
                conversation_preview=preview,
                recommendation=recommendation
            ))
        
        ranked.sort(key=lambda x: x.combined_score, reverse=True)
        
        for i, candidate in enumerate(ranked, 1):
            candidate.rank = i
        
        return ranked
    
    def _generate_recommendation(self, match: float, interest: float, combined: float) -> str:
        if combined >= 85:
            return "🔥 PRIORITY HIRE: Exceptional fit + high enthusiasm. Contact immediately!"
        elif combined >= 75:
            return "⚡ FAST-TRACK: Strong match, good interest. Schedule interview this week."
        elif combined >= 65:
            return "✅ RECOMMENDED: Solid fit, moderate interest. Good interview prospect."
        elif combined >= 55:
            return "📝 BACKUP: Decent on one dimension, weak on other. Keep in pipeline."
        else:
            return "❌ PASS: Low combined score. Focus on higher-ranked candidates."