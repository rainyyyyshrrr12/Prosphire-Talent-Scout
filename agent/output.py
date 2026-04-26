"""
Final Step: Generate recruiter-ready reports with full agent output.
Includes: ranked candidates, conversation transcripts, bias analysis, market intelligence, agent trace.
"""

import json
import os
from typing import List, Dict
from datetime import datetime
from agent.ranker import FinalRankedCandidate


class ReportGenerator:

    def generate_json_report(self, ranked: List[FinalRankedCandidate], jd: Dict,
                              conversations: Dict = None, bias_report: Dict = None,
                              market_intel: Dict = None, agent_trace: List = None) -> Dict:
        report = {
            "report_generated_at": datetime.now().isoformat(),
            "job_title": jd.get("title", "Unknown"),
            "job_location": jd.get("location", "Any"),
            "total_candidates_considered": len(ranked),
            "candidates": [],
            "summary": {
                "priority_hires": len([c for c in ranked if "PRIORITY" in c.recommendation]),
                "fast_track": len([c for c in ranked if "FAST-TRACK" in c.recommendation]),
                "recommended": len([c for c in ranked if "RECOMMENDED" in c.recommendation]),
                "average_match_score": round(sum(c.match_score for c in ranked) / len(ranked), 1) if ranked else 0,
                "average_interest_score": round(sum(c.interest_score for c in ranked) / len(ranked), 1) if ranked else 0
            }
        }

        for c in ranked:
            cand_data = c.to_dict()
            # Attach conversation transcript if available
            if conversations and c.candidate_id in conversations:
                cand_data["conversation_transcript"] = conversations[c.candidate_id]
            report["candidates"].append(cand_data)

        if bias_report:
            report["bias_analysis"] = bias_report
        if market_intel:
            report["market_intelligence"] = market_intel
        if agent_trace:
            report["agent_trace"] = [s.to_dict() if hasattr(s, 'to_dict') else s for s in agent_trace]

        return report

    def generate_markdown_report(self, ranked: List[FinalRankedCandidate], jd: Dict,
                                  conversations: Dict = None, bias_report: Dict = None,
                                  market_intel: Dict = None) -> str:
        """Full recruiter action report with all agent intelligence."""

        lines = [
            "# 🎯 AI Talent Scout — Recruiter Action Report",
            "",
            f"**Role:** {jd.get('title', 'Unknown')} | **Location:** {jd.get('location', 'Any')}",
            f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            "",
            "---",
            ""
        ]

        # Market Intelligence Section
        if market_intel:
            lines.extend([
                "## 📊 Market Intelligence",
                "",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Hiring Difficulty | {market_intel.get('hiring_difficulty', 'N/A')} |",
                f"| Talent Supply | {market_intel.get('talent_supply', 'N/A')} |",
                f"| Market Salary Range | {market_intel.get('salary_benchmark', {}).get('market_range', 'N/A')} |",
                f"| Salary Assessment | {market_intel.get('salary_benchmark', {}).get('assessment', 'N/A')} |",
                f"| Est. Time to Hire | {market_intel.get('estimated_time_to_hire', 'N/A')} |",
                "",
            ])
            recs = market_intel.get("recommendations", [])
            if recs:
                lines.append("**Recommendations:**")
                for r in recs:
                    lines.append(f"- {r}")
                lines.append("")
            lines.extend(["---", ""])

        # Bias Analysis Section
        if bias_report:
            lines.extend([
                "## ⚖️ JD Bias & Fairness Analysis",
                "",
                f"**Fairness Score:** {bias_report.get('fairness_score', 100)}/100",
                f"**Summary:** {bias_report.get('summary', 'No issues found')}",
                ""
            ])
            issues = bias_report.get("issues", [])
            if issues:
                lines.extend([
                    "| Issue | Type | Severity | Suggestion |",
                    "|-------|------|----------|------------|"
                ])
                for issue in issues[:5]:
                    lines.append(f"| {issue['term']} | {issue['type']} | {issue['severity']} | {issue['suggestion']} |")
                lines.append("")
            suggestions = bias_report.get("suggestions", [])
            if suggestions:
                for s in suggestions:
                    lines.append(f"- 💡 {s}")
                lines.append("")
            lines.extend(["---", ""])

        # Pipeline Summary
        lines.extend([
            "## 📋 Pipeline Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Candidates Evaluated | {len(ranked)} |",
            f"| Priority Hires | {len([c for c in ranked if 'PRIORITY' in c.recommendation])} |",
            f"| Fast-Track | {len([c for c in ranked if 'FAST-TRACK' in c.recommendation])} |",
            f"| Recommended | {len([c for c in ranked if 'RECOMMENDED' in c.recommendation])} |",
            f"| Avg Match Score | {round(sum(c.match_score for c in ranked) / len(ranked), 1) if ranked else 0}/100 |",
            f"| Avg Interest Score | {round(sum(c.interest_score for c in ranked) / len(ranked), 1) if ranked else 0}/100 |",
            "",
            "---",
            ""
        ])

        # Per-candidate one-pagers
        for c in ranked:
            interest_parts = c.conversation_preview.split(" | ") if c.conversation_preview else []
            enthusiasm = engagement = commitment = "N/A"
            if len(interest_parts) >= 3:
                try:
                    enthusiasm = interest_parts[0].split(": ")[1] if ": " in interest_parts[0] else "N/A"
                    engagement = interest_parts[1].split(": ")[1] if ": " in interest_parts[1] else "N/A"
                    commitment = interest_parts[2].split(": ")[1] if ": " in interest_parts[2] else "N/A"
                except IndexError:
                    pass

            if "PRIORITY" in c.recommendation:
                next_step, timeline = "Send offer discussion invite", "Within 24 hours"
            elif "FAST-TRACK" in c.recommendation:
                next_step, timeline = "Schedule technical interview", "This week"
            elif "RECOMMENDED" in c.recommendation:
                next_step, timeline = "Send culture-fit interview invite", "Next week"
            else:
                next_step, timeline = "Keep warm, reach out in 2 weeks", "Flexible"

            lines.extend([
                "",
                f"## #{c.rank} {c.candidate_name}",
                "",
                f"**{c.recommendation}**",
                "",
                "### Scores",
                "",
                f"| Score | Value | Breakdown |",
                f"|-------|-------|-----------|",
                f"| **Combined** | **{c.combined_score}/100** | Match × 60% + Interest × 40% |",
                f"| Match | {c.match_score}/100 | Skills {c.factor_breakdown.get('skills', {}).get('score', 0):.0f}/40 · Exp {c.factor_breakdown.get('experience', {}).get('score', 0):.0f}/25 · Salary {c.factor_breakdown.get('salary', {}).get('score', 0):.0f}/20 · Loc {c.factor_breakdown.get('location', {}).get('score', 0):.0f}/15 |",
                f"| Interest | {c.interest_score}/100 | Enthusiasm {enthusiasm} · Engagement {engagement} · Commitment {commitment} |",
                "",
                "### Why This Candidate?",
                "",
                "**Match Analysis:**",
                f"- ✅ Has: {', '.join(c.skill_breakdown.get('matched_skills', [])[:5]) if c.skill_breakdown.get('matched_skills') else 'N/A'}",
                f"- ❌ Missing: {', '.join(c.skill_breakdown.get('missing_skills', [])[:3]) if c.skill_breakdown.get('missing_skills') else 'None'}",
                f"- {c.factor_breakdown.get('experience', {}).get('note', 'N/A')}",
                f"- {c.factor_breakdown.get('salary', {}).get('note', 'N/A')}",
                f"- {c.factor_breakdown.get('location', {}).get('note', 'N/A')}",
                "",
                "**Interest Analysis:**",
                f"- {c.availability_timeline}",
                f"- ✅ Positive: {', '.join(c.enthusiasm_signals[:3]) if c.enthusiasm_signals else 'None recorded'}",
                f"- ⚠️ Concerns: {', '.join(c.concerns[:2]) if c.concerns else 'None'}",
                ""
            ])

            # Conversation Transcript
            if conversations and c.candidate_id in conversations:
                lines.extend(["### 💬 Conversation Transcript", ""])
                for turn in conversations[c.candidate_id]:
                    speaker = "🤖 Recruiter" if turn["speaker"] == "recruiter" else "👤 Candidate"
                    lines.append(f"**{speaker}:** {turn['message']}")
                    lines.append("")

            lines.extend([
                "### Recruiter Action",
                "",
                "```",
                f"Next Step: {next_step}",
                f"Timeline:  {timeline}",
                "```",
                "",
                "---"
            ])

        return "\n".join(lines)

    def save_reports(self, ranked: List[FinalRankedCandidate], jd: Dict,
                     conversations: Dict = None, bias_report: Dict = None,
                     market_intel: Dict = None, agent_trace: List = None,
                     output_dir: str = "output"):
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        json_report = self.generate_json_report(ranked, jd, conversations, bias_report, market_intel, agent_trace)
        json_path = f"{output_dir}/report_{ts}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)

        md_report = self.generate_markdown_report(ranked, jd, conversations, bias_report, market_intel)
        md_path = f"{output_dir}/report_{ts}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_report)

        return json_path, md_path