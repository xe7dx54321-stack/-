"""Signal fusion engine: fuses market expectation and team context into candidate signals."""
from dataclasses import dataclass, field


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


@dataclass
class FusedCandidate:
    candidate_id: str = ""
    match_id: str = ""
    selection_id: str = ""
    market_type: str = ""
    # Raw signals (may be negative)
    raw_base_signal: float = 0.0
    raw_score_adjustment: float = 0.0
    # Normalized / clamped scores (0–1)
    normalized_base_campaign_score: float = 0.0
    base_campaign_score: float = 0.0
    upgraded_campaign_score: float = 0.0
    fusion_score: float = 0.0
    score_adjustment: float = 0.0
    score_clamped: bool = False
    # Support signals
    market_supported: bool = False
    team_context_supported: bool = False
    missing_market_context: bool = False
    missing_team_context: bool = False
    low_quality_warning: bool = False
    # Bucket
    bucket: str = ""
    upgraded_bucket: str = ""
    # Status + review
    status: str = "unchanged"
    requires_review: bool = False
    review_reasons: list = field(default_factory=list)
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
    # Score guard fields
    min_base_campaign_score: float = 0.0
    max_base_campaign_score: float = 0.0
    min_upgraded_campaign_score: float = 0.0
    max_upgraded_campaign_score: float = 0.0
    min_fusion_score: float = 0.0
    max_fusion_score: float = 0.0
    raw_negative_signal_count: int = 0
    score_clamped_count: int = 0
    # Review guard fields
    review_triggered_by_unexplained_disagreement_count: int = 0
    review_triggered_by_missing_market_context_count: int = 0
    review_triggered_by_missing_team_context_count: int = 0
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

    def _is_list(x):
        return isinstance(x, list)
    def _dict(x):
        return isinstance(x, dict)

    for c in candidates:
        cid = c.get("candidate_id", c.get("selection_id", ""))
        mid = c.get("match_id", "")
        sel = c.get("selection_id", "")
        raw_base = float(c.get("campaign_score", c.get("ev", 0)))
        bucket = c.get("bucket", c.get("source_bucket", ""))

        # ---- Market alignment lookup ----
        aligned = False; major_disagree = False; has_alignment_record = False
        for ar in alignment_records if _is_list(alignment_records) else []:
            ak = ar.get("key", "") if _dict(ar) else getattr(ar, "key", "")
            if mid in ak and sel in ak:
                has_alignment_record = True
                st = ar.get("alignment_status", "") if _dict(ar) else getattr(ar, "alignment_status", "")
                if st == "aligned": aligned = True
                if st == "major_disagreement": major_disagree = True

        missing_mkt = not has_alignment_record

        # ---- Team context lookup ----
        ctx_supported = False; has_ctx_record = False
        for cs in context_signals if _is_list(context_signals) else []:
            team = cs.get("team", "") if _dict(cs) else getattr(cs, "team", "")
            ctx_sig = cs.get("context_signal", "") if _dict(cs) else getattr(cs, "context_signal", "")
            c_team = mid.split("_")[1] if "_" in mid else ""
            if (team in mid or c_team in team):
                has_ctx_record = True
                if ctx_sig in ("positive", "neutral"):
                    ctx_supported = True

        missing_ctx = not has_ctx_record

        # ---- Quality lookup ----
        qual = 0.5; has_qual_record = False
        for qs in quality_scores if _is_list(quality_scores) else []:
            qk = qs.get("key", "") if _dict(qs) else getattr(qs, "key", "")
            if mid in qk and sel in qk:
                has_qual_record = True
                qual = qs.get("score", 0.5) if _dict(qs) else getattr(qs, "score", 0.5)

        low_qual = qual < 0.4

        # ---- Score normalization (0–1 clamp) ----
        norm_base = _clamp(raw_base, 0.0, 1.0)
        score_clamped = (raw_base < 0.0 or raw_base > 1.0)
        if raw_base < 0.0:
            summary.raw_negative_signal_count += 1

        # ---- Score adjustment ----
        adj = 0.0
        if aligned: adj += mkt_weight
        if ctx_supported: adj += ctx_weight
        adj += (qual - 0.5) * qual_weight
        if major_disagree: adj -= 0.1
        raw_adj = adj
        adj = max(min_adj, min(max_adj, adj))

        upgraded_raw = norm_base + adj
        upgraded = _clamp(upgraded_raw, 0.0, 1.0)
        if upgraded_raw < 0.0 or upgraded_raw > 1.0:
            score_clamped = True

        fusion_score = _clamp(upgraded, 0.0, 1.0)
        if score_clamped:
            summary.score_clamped_count += 1

        # ---- Review guard ----
        review_reasons = []
        requires_review = False

        # unexplained disagreement → review
        if major_disagree and not aligned:
            review_reasons.append("unexplained_market_disagreement")
            requires_review = True
            summary.review_triggered_by_unexplained_disagreement_count += 1

        # missing market context → warning + review if upgraded
        if missing_mkt:
            review_reasons.append("missing_market_context")
            summary.review_triggered_by_missing_market_context_count += 1
            if adj >= promo_thresh:
                requires_review = True

        # missing team context → warning + review if upgraded
        if missing_ctx:
            review_reasons.append("missing_team_context")
            summary.review_triggered_by_missing_team_context_count += 1
            if adj >= promo_thresh:
                requires_review = True

        if low_qual:
            review_reasons.append("low_signal_quality")
            requires_review = True

        # ---- Status determination ----
        status = "unchanged"
        if adj >= promo_thresh:
            status = "promoted"; summary.promoted_count += 1
        elif adj <= demo_thresh:
            status = "demoted"; summary.demoted_count += 1

        if requires_review and status not in ("promoted", "demoted"):
            status = "review_required"
        if requires_review:
            summary.review_required_count += 1

        if qual < 0.25:
            status = "watch_only"; summary.watch_only_count += 1

        # ---- Bucket upgrade ----
        up_bucket = bucket
        if adj >= promo_thresh and bucket == "edge":
            up_bucket = "core"
        elif adj <= demo_thresh and bucket == "core":
            up_bucket = "edge"
        # Major unexplained disagreement blocks Core eligibility
        if major_disagree and not aligned and up_bucket == "core":
            up_bucket = "watch_only"
            review_reasons.append("major_disagreement_blocks_core")

        fc = FusedCandidate(
            candidate_id=cid, match_id=mid, selection_id=sel,
            market_type=c.get("market_type", ""),
            raw_base_signal=round(raw_base, 4),
            raw_score_adjustment=round(raw_adj, 4),
            normalized_base_campaign_score=round(norm_base, 4),
            base_campaign_score=round(norm_base, 4),
            upgraded_campaign_score=round(upgraded, 4),
            fusion_score=round(fusion_score, 4),
            score_adjustment=round(adj, 4),
            score_clamped=score_clamped,
            market_supported=aligned,
            team_context_supported=ctx_supported,
            missing_market_context=missing_mkt,
            missing_team_context=missing_ctx,
            low_quality_warning=low_qual,
            bucket=bucket,
            upgraded_bucket=up_bucket,
            status=status,
            requires_review=requires_review,
            review_reasons=review_reasons,
            notes=[]
        )
        summary.candidates.append(fc)
        summary.fused_signal_count += 1
        if adj != 0: summary.upgraded_candidate_count += 1
        if aligned: summary.market_supported_count += 1
        if ctx_supported: summary.team_context_supported_count += 1
        if low_qual: summary.low_quality_warning_count += 1
        if major_disagree and not aligned: summary.unexplained_disagreement_count += 1

    # ---- Score guard aggregates ----
    if summary.candidates:
        summary.min_base_campaign_score = round(min(c.base_campaign_score for c in summary.candidates), 4)
        summary.max_base_campaign_score = round(max(c.base_campaign_score for c in summary.candidates), 4)
        summary.min_upgraded_campaign_score = round(min(c.upgraded_campaign_score for c in summary.candidates), 4)
        summary.max_upgraded_campaign_score = round(max(c.upgraded_campaign_score for c in summary.candidates), 4)
        summary.min_fusion_score = round(min(c.fusion_score for c in summary.candidates), 4)
        summary.max_fusion_score = round(max(c.fusion_score for c in summary.candidates), 4)

    if summary.fused_signal_count == 0:
        summary.warnings.append("No candidates fused; check source data availability.")
    return summary
