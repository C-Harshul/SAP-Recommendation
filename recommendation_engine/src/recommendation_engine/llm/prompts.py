"""Prompt templates per pipeline stage."""

EXTRACT_SYSTEM = """You extract structured mission ideas from user research.
Rules (non-negotiable):
- Every idea MUST include verbatim evidence_quotes copied from the source text.
- Do NOT synthesize or invent quotes.
- Tag specificity as vague | specific | actionable.
- If the user only describes a problem with no solution, set proposed_solution to null.
- Return at most 8 distinct ideas per source; keep fields concise so the JSON completes.
- Output valid JSON only — no trailing commas, no truncated objects.
Return JSON matching the schema exactly."""

EXTRACT_USER_INTERVIEW = """Extract all distinct ideas from this interview.

Participant role: {role}
Interview ID: {interview_id}

Transcript:
{transcript}
"""

EXTRACT_USER_COMMUNITY = """Extract all distinct ideas from this community post.

Author role: {role}
Post ID: {post_id}
Upvotes: {upvotes}

Body:
{body}
"""

SYNTHESIZE_SYSTEM = """You propose 2-3 prototype-scale solutions for a user problem.
Use the provided market trends as inspiration only — do not claim users asked for these solutions.
Mark solutions as creative extensions grounded in industry direction.
Return JSON matching the schema."""

SYNTHESIZE_USER = """Problem (from interview, problem-only):
{pain_point}

Evidence quotes:
{quotes}

Related market trends:
{trends}
"""

CLUSTER_SYSTEM = """Write a single canonical cluster statement that stays close to source language.
Do not add new claims. Return JSON with canonical_statement only."""

CLUSTER_USER = """Merge these related idea statements into one canonical pain/opportunity:

{statements}
"""

CLUSTER_BATCH_SYSTEM = """For each numbered cluster below, write one canonical_statement.
Stay close to source language; do not add new claims.
Return JSON with clusters: [{cluster_index, canonical_statement}, ...] for every index shown."""

CLUSTER_BATCH_USER = """Canonicalize each cluster (use the exact cluster_index from headers):

{clusters_block}
"""

SYNTHESIZE_BATCH_SYSTEM = """For each numbered problem, propose 2-3 prototype-scale solutions.
Use provided market trends as inspiration only.
Return JSON with problems: [{problem_index, solutions: [{solution_text, approach}, ...]}, ...]."""

SYNTHESIZE_BATCH_USER = """Synthesize solutions for each problem below:

{problems_block}
"""

RANK_BATCH_SYSTEM = """Score each numbered mission cluster for SAP Experience Garage prioritization.
All scores 0.0–1.0 per cluster. Return JSON rankings with cluster_index and five scores + rationale."""

RANK_BATCH_USER = """Score each cluster:

{clusters_block}
"""

RANK_QUALITATIVE_SYSTEM = """Score this mission cluster for SAP Experience Garage prioritization.
All scores 0.0–1.0. Be honest — low market_validation if trends are weak or unrelated.
Return JSON with: signal_urgency, market_validation, sap_relevance, feasibility, novelty, rationale."""

RANK_QUALITATIVE_USER = """Canonical cluster:
{canonical}

Source count (distinct interviews + posts): {source_count}
Specificity mix: {specificity_note}
Related market trends:
{trends}
"""

WRITEUP_SYSTEM = """Write a mission proposal with exactly 5 sections in the JSON schema.
Rules:
- Cite user quotes in why_this_matters.
- Cite trend URLs in industry_context.
- If feasibility < 0.5, risks section must address technical risks honestly.
- If market_validation < 0.5, industry_context must state this is user-driven without industry validation.
- Connect suggested_approach to the latest tech from cited trends."""

TREND_ENRICH_SYSTEM = """You enrich raw market-trend bronze records into structured trend signals.
For each item: concise theme, 2-3 sentence summary, momentum (rising|stable|fading), novelty (new|emerging|established).
Preserve trend_id and evidence_urls from input. Do not invent URLs."""

TREND_ENRICH_USER = """Enrich these bronze-derived market signals:

{items}
"""

WRITEUP_USER = """Cluster: {canonical}

Scores:
- feasibility: {feasibility}
- market_validation: {market_validation}
- impact_score: {impact_score}
- effort_score: {effort_score}

User evidence:
{evidence}

Market trends:
{trends}
"""
