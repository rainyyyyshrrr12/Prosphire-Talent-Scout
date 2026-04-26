"""
AI Talent Scout — Agentic Orchestrator
Implements a ReAct-style (Reason → Act → Observe) agent loop.
The agent autonomously plans, executes tools, and makes decisions.
"""

import time
import traceback
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

from agent.jd_parser import JDParser
from agent.discovery import CandidateDiscovery
from agent.matcher import CandidateMatcher
from agent.conversation_engine import ConversationEngine
from agent.interest_analyzer import InterestAnalyzer
from agent.ranker import CandidateRanker
from agent.bias_detector import BiasDetector
from agent.market_intel import MarketIntelligence
from agent.output import ReportGenerator


@dataclass
class AgentStep:
    """A single step in the agent's reasoning trace."""
    step_number: int
    phase: str          # "think", "act", "observe", "decide"
    action: str         # What the agent did
    detail: str         # Detailed explanation
    timestamp: float    # Unix timestamp
    duration_ms: float = 0.0  # How long this step took
    data: Optional[Dict] = None  # Optional structured data

    def to_dict(self) -> Dict:
        d = asdict(self)
        d.pop("data", None)  # Don't serialize large data blobs
        return d


@dataclass
class AgentResult:
    """Complete result of an agent run."""
    success: bool
    job_title: str = ""
    job_location: str = ""
    ranked_candidates: List = field(default_factory=list)
    jd_parsed: Dict = field(default_factory=dict)
    trace: List[AgentStep] = field(default_factory=list)
    bias_report: Dict = field(default_factory=dict)
    market_intel: Dict = field(default_factory=dict)
    conversations: Dict = field(default_factory=dict)  # candidate_id -> conversation turns
    total_duration_seconds: float = 0.0
    error: Optional[str] = None
    stats: Dict = field(default_factory=dict)


class TalentScoutAgent:
    """
    Autonomous AI Agent for talent scouting.
    
    Uses a ReAct (Reason-Act-Observe) loop to:
    1. Parse and understand job descriptions
    2. Search and discover matching candidates
    3. Evaluate deep match with explainability
    4. Simulate conversational outreach
    5. Analyze interest signals
    6. Produce ranked, actionable output
    
    The agent makes autonomous decisions at each step:
    - Adjusts search thresholds based on results
    - Decides outreach strategy per candidate
    - Flags bias and market concerns
    """

    def __init__(self):
        self.step_count = 0
        self.trace: List[AgentStep] = []
        self.callbacks = []  # Progress callbacks for SSE

    def add_callback(self, callback):
        """Register a progress callback function."""
        self.callbacks.append(callback)

    def _emit(self, phase: str, action: str, detail: str, data: Optional[Dict] = None):
        """Record a step in the agent trace and notify callbacks."""
        self.step_count += 1
        step = AgentStep(
            step_number=self.step_count,
            phase=phase,
            action=action,
            detail=detail,
            timestamp=time.time(),
            data=data
        )
        self.trace.append(step)

        # Notify progress callbacks
        for cb in self.callbacks:
            try:
                cb(step)
            except Exception:
                pass

        return step

    def think(self, reasoning: str):
        """Agent reasoning step — what it's thinking."""
        return self._emit("think", "Reasoning", reasoning)

    def act(self, action: str, detail: str, data=None):
        """Agent action step — what it's doing."""
        return self._emit("act", action, detail, data)

    def observe(self, observation: str, data=None):
        """Agent observation step — what it learned."""
        return self._emit("observe", "Observed", observation, data)

    def decide(self, decision: str):
        """Agent decision step — autonomous choice."""
        return self._emit("decide", "Decision", decision)

    def run(self, jd_text: str, min_match_score: float = 45.0, top_k: int = 10, pool_path: str = None) -> AgentResult:
        """
        Execute the full agentic talent scouting pipeline.
        Returns AgentResult with trace, candidates, and analysis.
        """
        start_time = time.time()
        result = AgentResult(success=False)

        try:
            # ─── STEP 1: Understand the JD ───
            self.think("Received a job description. I need to parse it to extract structured requirements — title, skills, experience, salary, location.")
            
            t0 = time.time()
            self.act("Parsing JD", f"Sending {len(jd_text)} characters to LLM for intelligent parsing...")
            
            parser = JDParser()
            jd = parser.parse(jd_text)
            
            parse_time = (time.time() - t0) * 1000
            exp = jd.get("experience_years", {})
            sal = jd.get("salary_range_lpa", {})
            self.observe(
                f"Parsed successfully: '{jd.get('title', 'Unknown')}' at {jd.get('location', 'Any')}. "
                f"Found {len(jd.get('required_skills', []))} required skills, "
                f"{len(jd.get('nice_to_have', []))} nice-to-haves. "
                f"Experience: {exp.get('min') or 0}-{exp.get('max') or 10} years. "
                f"Salary: ₹{sal.get('min') or 0}-{sal.get('max') or 0} LPA."
            )
            
            result.jd_parsed = jd
            result.job_title = jd.get("title", "Unknown")
            result.job_location = jd.get("location", "Any")

            if not jd.get("title") or not jd.get("required_skills"):
                self.decide("JD parsing failed — insufficient information extracted. Aborting.")
                result.error = "Could not parse JD. Please include a clear job title and requirements."
                return result

            # ─── STEP 1.5: Bias Detection ───
            self.think("Before proceeding, I should check the JD for any biased or exclusionary language that could limit our talent pool unfairly.")
            self.act("Analyzing JD for bias", "Scanning for gendered terms, age-exclusive language, unnecessary requirements...")
            
            bias = BiasDetector()
            bias_report = bias.analyze_jd(jd_text, jd)
            result.bias_report = bias_report
            
            if bias_report.get("issues_found", 0) > 0:
                self.observe(f"⚠️ Found {bias_report['issues_found']} potential bias issues: {', '.join(bias_report.get('issue_types', []))}")
                self.decide(f"Flagging {bias_report['issues_found']} bias concerns for recruiter review, but proceeding with search.")
            else:
                self.observe("No significant bias detected in the JD. Proceeding with search.")

            # ─── STEP 1.6: Market Intelligence ───
            self.think("Let me assess the talent market for this role to provide context to the recruiter.")
            self.act("Generating market intelligence", f"Analyzing market conditions for '{jd.get('title')}' roles...")
            
            market = MarketIntelligence()
            market_intel = market.analyze(jd)
            result.market_intel = market_intel
            
            self.observe(
                f"Market assessment: Difficulty={market_intel.get('hiring_difficulty', 'Unknown')}. "
                f"Benchmark salary: ₹{market_intel.get('salary_benchmark', {}).get('market_median', 'N/A')} LPA. "
                f"Supply: {market_intel.get('talent_supply', 'Unknown')}."
            )

            # ─── STEP 2: Discover Candidates ───
            self.think(f"Now I need to search the talent pool. I'll look for candidates matching the required skills: {', '.join(jd.get('required_skills', [])[:5])}.")
            
            t0 = time.time()
            self.act("Searching talent pool", "Running multi-signal discovery: skill overlap, experience fit, location, salary alignment...")
            
            discovery = CandidateDiscovery(pool_path=pool_path)
            pool_stats = discovery.get_pool_stats()
            self.observe(f"Data source: {pool_stats.get('source_file', 'unknown')}")
            discovered = discovery.discover(jd, max_results=top_k * 3)
            
            self.observe(f"Searched {pool_stats['total_candidates_in_pool']} candidates. Found {len(discovered)} potential matches above discovery threshold.")

            # ─── Autonomous Decision: Adjust if too few ───
            if len(discovered) < 3:
                self.think(f"Only {len(discovered)} candidates found. This is below my minimum threshold of 3. I should widen the search.")
                self.decide("Lowering discovery threshold to find more candidates.")
                discovered = discovery.discover(jd, max_results=top_k * 4)
                self.observe(f"Widened search found {len(discovered)} candidates.")

            if not discovered:
                self.decide("No candidates found even with widened search. The JD requirements may be too niche for the current talent pool.")
                result.error = "No matching candidates found in talent pool."
                return result

            # ─── STEP 3: Deep Match ───
            self.think(f"I have {len(discovered)} candidates from discovery. Now I need deep matching — scoring each on skills (40%), experience (25%), salary (20%), location (15%).")
            
            t0 = time.time()
            self.act("Deep matching candidates", f"Evaluating {len(discovered)} candidates with multi-factor scoring + semantic skill matching...")
            
            matcher = CandidateMatcher()
            candidate_pool = [d.candidate for d in discovered]
            matches = matcher.find_matches(jd, candidate_pool, min_score=min_match_score, top_k=top_k)
            
            match_time = (time.time() - t0) * 1000
            self.observe(f"{len(matches)} candidates passed deep matching (threshold: {min_match_score}). Top match: {matches[0].candidate_name} ({matches[0].match_score}/100)." if matches else "No candidates passed matching threshold.")

            # ─── Autonomous Decision: Adjust threshold ───
            if len(matches) < 3 and min_match_score > 35:
                original_count = len(matches)
                self.think(f"Only {len(matches)} candidates passed at threshold {min_match_score}. Lowering to {min_match_score - 10} to build a better shortlist.")
                self.decide(f"Reducing match threshold from {min_match_score} to {min_match_score - 10}")
                matches = matcher.find_matches(jd, candidate_pool, min_score=min_match_score - 10, top_k=top_k)
                self.observe(f"Widened threshold found {len(matches)} candidates (was {original_count}).")

            if not matches:
                self.decide("No candidates met minimum match threshold even after adjustment.")
                result.error = "No candidates met minimum match threshold."
                return result

            # ─── STEP 4: Conversational Outreach ───
            self.think(f"Now the critical step: I'll simulate personalized outreach conversations with {len(matches)} candidates to gauge genuine interest.")
            
            t0 = time.time()
            conv_engine = ConversationEngine()
            analyzer = InterestAnalyzer()
            interest_signals = []
            conversations = {}

            for i, match in enumerate(matches):
                try:
                    self.act(
                        f"Outreach to {match.candidate_name}",
                        f"Simulating 6-turn recruiter-candidate conversation ({i+1}/{len(matches)})..."
                    )

                    conversation = conv_engine.generate_conversation(match.raw_candidate, jd)
                    conversations[match.candidate_id] = [
                        {"turn": t.turn_number, "speaker": t.speaker, "message": t.message, "intent": t.intent}
                        for t in conversation
                    ]

                    signals = analyzer.analyze(conversation, match.raw_candidate)
                    signals.candidate_id = match.candidate_id
                    signals.candidate_name = match.candidate_name
                    interest_signals.append(signals)

                    self.observe(
                        f"{match.candidate_name}: Interest={signals.total_interest_score}/100 "
                        f"(Enthusiasm {signals.enthusiasm_score}/40, Engagement {signals.engagement_score}/30, "
                        f"Commitment {signals.commitment_score}/30). "
                        f"{len(signals.positive_signals)} positive signals, {len(signals.negative_signals)} concerns."
                    )

                except Exception as e:
                    self.observe(f"⚠️ Conversation with {match.candidate_name} failed: {str(e)[:80]}. Skipping candidate.")
                    # Create default signals so we don't lose the match data
                    from agent.interest_analyzer import InterestSignals
                    default_signals = InterestSignals(
                        candidate_id=match.candidate_id,
                        candidate_name=match.candidate_name,
                        enthusiasm_score=20.0,
                        engagement_score=10.0,
                        commitment_score=15.0,
                        total_interest_score=45.0,
                        positive_signals=[],
                        negative_signals=["Conversation simulation failed"],
                        availability_commitment="Unknown — conversation could not be completed"
                    )
                    interest_signals.append(default_signals)

            result.conversations = conversations
            conv_time = (time.time() - t0) * 1000

            # ─── STEP 5: Rank ───
            self.think(f"All conversations complete. Now combining Match Score (60% weight) and Interest Score (40% weight) for final ranking.")
            
            self.act("Final ranking", f"Combining scores for {len(matches)} candidates using weighted formula...")
            
            ranker = CandidateRanker()
            ranked = ranker.rank_candidates(matches, interest_signals)
            
            # Summary stats
            priority = len([c for c in ranked if "PRIORITY" in c.recommendation])
            fasttrack = len([c for c in ranked if "FAST-TRACK" in c.recommendation])
            recommended = len([c for c in ranked if "RECOMMENDED" in c.recommendation])
            
            self.observe(
                f"Final ranking complete: {len(ranked)} candidates. "
                f"Priority: {priority}, Fast-Track: {fasttrack}, Recommended: {recommended}. "
                f"Top candidate: {ranked[0].candidate_name} ({ranked[0].combined_score}/100)." if ranked else "No candidates ranked."
            )

            # ─── STEP 6: Final Decision & Recommendations ───
            self.think("Let me provide my final assessment and actionable recommendations for the recruiter.")
            
            if priority > 0:
                self.decide(f"🔥 Strong pipeline! {priority} priority hire(s) identified. Recruiter should contact immediately.")
            elif fasttrack > 0:
                self.decide(f"⚡ Good pipeline. {fasttrack} fast-track candidate(s). Schedule interviews this week.")
            elif recommended > 0:
                self.decide(f"✅ Viable candidates found. {recommended} recommended for interview. Pipeline needs nurturing.")
            else:
                self.decide("📝 Weak pipeline. Consider revising JD requirements or expanding search channels.")

            result.success = True
            result.ranked_candidates = ranked
            result.stats = {
                "pool_size": pool_stats["total_candidates_in_pool"],
                "discovered": len(discovered),
                "matched": len(matches),
                "conversations_completed": len(conversations),
                "priority_hires": priority,
                "fast_track": fasttrack,
                "recommended": recommended,
            }

        except Exception as e:
            self.observe(f"❌ Agent error: {str(e)}")
            traceback.print_exc()
            result.error = str(e)

        result.trace = self.trace
        result.total_duration_seconds = round(time.time() - start_time, 2)
        return result
