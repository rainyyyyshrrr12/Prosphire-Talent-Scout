#!/usr/bin/env python3
"""
AI-Powered Talent Scouting & Engagement Agent — CLI Interface
Uses the agentic orchestrator for autonomous pipeline execution.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.llm_engine import FreeLLMEngine
from agent.orchestrator import TalentScoutAgent
from agent.output import ReportGenerator

load_dotenv()


def run_agent(jd_path: str, min_match_score: float = 45.0, top_k: int = 10):

    print("=" * 75)
    print("  AI TALENT SCOUT AGENT v3.0 — Agentic Pipeline")
    print("=" * 75)

    # Validate API keys
    llm = FreeLLMEngine()
    status = llm.get_status()
    if not any([status["groq"], status["google"], status["openrouter"]]):
        print("\n❌ No API keys configured!")
        print("Add at least one key to your .env file:")
        print("  GROQ_API_KEY=your_key")
        print("  GOOGLE_API_KEY=your_key")
        print("  OPENROUTER_API_KEY=your_key")
        return None

    active = [k for k, v in status.items() if v and k != "active_provider"]
    print(f"\n🔑 API Providers Ready: {', '.join(active).upper()}")

    # Load JD
    print(f"\n📄 Loading Job Description from: {jd_path}")
    if not os.path.exists(jd_path):
        print(f"❌ File not found: {jd_path}")
        return None

    with open(jd_path, 'r', encoding='utf-8') as f:
        jd_text = f.read()

    if len(jd_text.strip()) < 50:
        print("❌ JD too short (minimum 50 characters)")
        return None

    print(f"   Loaded: {len(jd_text)} characters")

    # Run the agent
    print("\n Starting Agent...\n")

    def print_step(step):
        icons = {"think": "💭", "act": "⚙️", "observe": "👁️", "decide": "🧠"}
        icon = icons.get(step.phase, "•")
        print(f"  {icon} [{step.phase.upper()}] {step.detail}")

    agent = TalentScoutAgent()
    agent.add_callback(print_step)
    result = agent.run(jd_text, min_match_score=min_match_score, top_k=top_k)

    if not result.success:
        print(f"\n❌ Agent failed: {result.error}")
        return None

    # Save reports
    print(f"\n📊 Generating Reports...")
    generator = ReportGenerator()
    json_path, md_path = generator.save_reports(
        result.ranked_candidates, result.jd_parsed,
        conversations=result.conversations,
        bias_report=result.bias_report,
        market_intel=result.market_intel,
        agent_trace=result.trace
    )
    print(f"   JSON: {json_path}")
    print(f"   Markdown: {md_path}")

    # Final Summary
    print("\n" + "=" * 75)
    print("  📋 FINAL SHORTLIST — RECRUITER DASHBOARD")
    print("=" * 75)

    for c in result.ranked_candidates:
        if c.combined_score >= 85:
            tier = "🔥 PRIORITY"
        elif c.combined_score >= 75:
            tier = "⚡ FAST-TRACK"
        elif c.combined_score >= 65:
            tier = "✅ RECOMMENDED"
        else:
            tier = "📝 BACKUP"

        print(f"\n  {tier} #{c.rank} {c.candidate_name}")
        print(f"    Combined: {c.combined_score}/100 | Match: {c.match_score} | Interest: {c.interest_score}")
        print(f"    {c.recommendation}")

    print(f"\n  ⏱️ Total time: {result.total_duration_seconds}s")
    print(f"  📁 Reports: output/")
    print("=" * 75)

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Talent Scout Agent")
    parser.add_argument("--jd", default="demo/sample_jd.txt", help="Path to JD file")
    parser.add_argument("--min-score", type=float, default=45.0, help="Minimum match score")
    parser.add_argument("--top-k", type=int, default=10, help="Max candidates")

    args = parser.parse_args()
    result = run_agent(args.jd, args.min_score, args.top_k)
    if result is None:
        sys.exit(1)