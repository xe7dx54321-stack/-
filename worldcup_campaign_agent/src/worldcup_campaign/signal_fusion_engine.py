"""Signal fusion engine: fuses market expectation and team context into candidate signals."""
from dataclasses import dataclass, field


@dataclass
class FusedCandidate:
    candidate_id: str = ""
    match_id: str = ""
    selection_id: str = ""
    market_type: str = ""
    base_campaign_score: float = 0.0
    upgraded_campaign_score: float = 0.0
    score_adjustment: float = 0.0
    market_supported: bool = False
    team_context_supported: bool = False
    low_quality_warning: bool = False
    bucket: str = ""
    upgraded_bucket: str = ""
    status: str = "unchanged"
    notes: list = field(default_factory=list)


@dataclass
class FusionSummary:
    candidates: list = field(default_factory=list)
    candidate_count: int = 0
    fused_signal_count: int = 0
    upgraded_candidate_count: int = 0
    promoted_count: int = 0
    demoted_count: int = 0
    review_required_count: int = 0
    watch_only_count: int = 0
    market_supported_count: int = 0
    team_context_supported_count: int = 0
    low_quality_warning_count: int = 0
    unexplained_disagreement_count: int = 0
    warnings: list = field(default_factory=list)


def fuse_signals(
    candidates: list,
    alignment_records: list,
    context_signals: list,
    quality_scores: list,
    config: dict
) -> FusionSummary:
    fusion_cfg = config.get("fusion", {})
    mkt_weight = fusion_cfg.get("market_support_weight", 0.20)
    ctx_weight = fusion_cfg.get("team_context_weight", 0.15)
    qual_weight = fusion_cfg.get("signal_quality_weight", 0.10)
    max_adj = fusion_cfg.get("max_campaign_score_adjustment", 0.25)
    min_adj = fusion_cfg.get("min_campaign_score_adjustment", -0.15)
    promo_thresh = fusion_cfg.get("promotion_threshold", 0.10)
    demo_thresh = fusion_cfg.get("demotion_threshold", -0.05)

    summary = FusionSummary()
    summary.candidate_count = len(candidates)

    for c in candidates:
        cid = c.get("candidate_id", c.get("selection_id", ""))
        mid = c.get("match_id", "")
        sel = c.get("selection_id", "")
        base_score = float(c.get("campaign_score", c.get("ev", 0)))
        bucket = c.get("bucket", c.get("source_bucket", ""))

        # Market alignment lookup
        aligned = False; major_disagree = False
        for ar in alignment_records if isinstance(alignment_records, list) else []:
            ak = ar.get("key", "") if isinstance(ar, dict) else getattr(ar, "key", "")
            if mid in ak and sel in ak:
                status = ar.get("alignment_status", "") if isinstance(ar, dict) else getattr(ar, "alignment_status", "")
                if status == "aligned": aligned = True
                if status == "major_disagreement": major_disagree = True

        # Team context lookup
        ctx_supported = False
        for cs in context_signals if isinstance(context_signals, list) else []:
            team = cs.get("team", "") if isinstance(cs, dict) else getattr(cs, "team", "")
            ctx_sig = cs.get("context_signal", "") if isinstance(cs, dict) else getattr(cs, "context_signal", "")
            c_team = mid.split("_")[1] if "_" in mid else ""
            if (team in mid or c_team in team) and ctx_sig in ("positive", "neutral"):
                ctx_supported = True

        # Quality lookup
        qual = 0.5
        for qs in quality_scores if isinstance(quality_scores, list) else []:
            qk = qs.get("key", "") if isinstance(qs, dict) else getattr(qs, "key", "")
            if mid in qk and sel in qk:
                qual = qs.get("score", 0.5) if isinstance(qs, dict) else getattr(qs, "score", 0.5)

        low_qual = qual < 0.4

        # Score adjustment
        adj = 0.0
        if aligned: adj += mkt_weight
        if ctx_supported: adj += ctx_weight
        adj += (qual - 0.5) * qual_weight
        if major_disagree: adj -= 0.1
        adj = max(min_adj, min(max_adj, adj))
        upgraded = round(base_score + adj, 4)

        # Status determination
        status = "unchanged"
        if adj >= promo_thresh:
            status = "promoted"; summary.promoted_count += 1
        elif adj <= demo_thresh:
            status = "demoted"; summary.demoted_count += 1
        if low_qual:
            status = "review_required"; summary.review_required_count += 1
        if qual < 0.25:
            status = "watch_only"; summary.watch_only_count += 1

        # Bucket upgrade
        up_bucket = bucket
        if adj >= promo_thresh and bucket == "edge":
            up_bucket = "core"
        elif adj <= demo_thresh and bucket == "core":
            up_bucket = "edge"

        fc = FusedCandidate(
            candidate_id=cid, match_id=mid, selection_id=sel,
            market_type=c.get("market_type", ""),
            base_campaign_score=base_score,
            upgraded_campaign_score=upgraded,
            score_adjustment=round(adj, 4),
            market_supported=aligned,
            team_context_supported=ctx_supported,
            low_quality_warning=low_qual,
            bucket=bucket, upgraded_bucket=up_bucket,
            status=status,
            notes=[]
        )
        summary.candidates.append(fc)
        summary.fused_signal_count += 1
        if adj != 0: summary.upgraded_candidate_count += 1
        if aligned: summary.market_supported_count += 1
        if ctx_supported: summary.team_context_supported_count += 1
        if low_qual: summary.low_quality_warning_count += 1
        if major_disagree and not aligned: summary.unexplained_disagreement_count += 1

    if summary.fused_signal_count == 0:
        summary.warnings.append("No candidates fused; check source data availability.")
    return summary
