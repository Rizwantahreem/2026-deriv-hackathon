"""
AI Risk Scoring Engine — Gemini-powered fraud and risk assessment.

Runs AFTER OCR analysis to evaluate:
- Name consistency (OCR vs form, transliteration)
- Document age/expiry risk
- Cross-field consistency (DOB, address, postal code)
- Quality anomalies (unusually perfect = screenshot risk)
- Data mismatch severity

Returns: risk_level (LOW/MEDIUM/HIGH), risk_score (0-100),
risk_factors list, recommendation (auto-approve/manual-review/reject)
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Recommendation(str, Enum):
    AUTO_APPROVE = "auto-approve"
    MANUAL_REVIEW = "manual-review"
    REJECT = "reject"


@dataclass
class RiskAssessment:
    """Result of AI risk assessment."""
    risk_level: RiskLevel
    risk_score: int  # 0 (no risk) to 100 (extreme risk)
    risk_factors: List[Dict[str, str]]
    recommendation: Recommendation
    reasoning: str
    ai_generated: bool = True


# ============================================================================
# RULE-BASED RISK ENGINE (fast, always available)
# ============================================================================

def _rule_based_risk(
    ocr_data: Dict[str, Any],
    form_data: Dict[str, Any],
    quality_score: int,
    mismatches: List[Dict],
    country_code: str,
) -> RiskAssessment:
    """
    Fast rule-based risk scoring. Always works (no API call needed).
    Used as primary scorer and as fallback when Gemini is unavailable.
    """
    risk_score = 0
    risk_factors = []

    # 1. Data mismatches (most important signal)
    if mismatches:
        mismatch_count = len(mismatches)
        mismatch_penalty = min(mismatch_count * 20, 50)
        risk_score += mismatch_penalty
        for m in mismatches:
            risk_factors.append({
                "factor": "data_mismatch",
                "field": m.get("field", "unknown"),
                "severity": "high",
                "detail": f"Form: '{m.get('form_value', '?')}' vs Document: '{m.get('document_value', '?')}'"
            })

    # 2. Quality anomalies
    if quality_score >= 98:
        risk_score += 10
        risk_factors.append({
            "factor": "quality_anomaly",
            "severity": "medium",
            "detail": f"Unusually high quality score ({quality_score}/100) — possible digital copy or screenshot"
        })
    elif quality_score < 30:
        risk_score += 15
        risk_factors.append({
            "factor": "low_quality",
            "severity": "medium",
            "detail": f"Very low quality ({quality_score}/100) — document may be intentionally obscured"
        })

    # 3. Missing critical OCR fields
    critical_fields_by_country = {
        "PK": ["cnic_number", "name_english", "name"],
        "IN": ["aadhaar_number", "name"],
        "GB": ["surname", "given_names", "passport_number", "license_number"],
    }
    expected = critical_fields_by_country.get(country_code, ["name"])
    if ocr_data:
        missing_critical = [
            f for f in expected
            if not ocr_data.get(f) or str(ocr_data.get(f, "")).lower() in ("null", "none", "")
        ]
        if missing_critical:
            risk_score += len(missing_critical) * 8
            risk_factors.append({
                "factor": "missing_fields",
                "severity": "medium",
                "detail": f"Could not extract: {', '.join(missing_critical)}"
            })

    # 4. Document expiry check
    expiry = ocr_data.get("expiry_date") or ocr_data.get("expiration_date") if ocr_data else None
    if expiry:
        from datetime import datetime, date
        try:
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    exp_date = datetime.strptime(str(expiry), fmt).date()
                    if exp_date < date.today():
                        risk_score += 30
                        risk_factors.append({
                            "factor": "expired_document",
                            "severity": "high",
                            "detail": f"Document expired on {expiry}"
                        })
                    break
                except ValueError:
                    continue
        except Exception:
            pass

    # 5. Name consistency check (fuzzy)
    form_name = str(form_data.get("full_name") or form_data.get("first_name", "") + " " + form_data.get("last_name", "")).strip().lower()
    ocr_name = str(ocr_data.get("name") or ocr_data.get("name_english") or ocr_data.get("given_names", "") + " " + ocr_data.get("surname", "")).strip().lower() if ocr_data else ""

    if form_name and ocr_name and form_name != "none" and ocr_name != "none":
        # Simple character overlap check
        form_chars = set(form_name.replace(" ", ""))
        ocr_chars = set(ocr_name.replace(" ", ""))
        if form_chars and ocr_chars:
            overlap = len(form_chars & ocr_chars) / max(len(form_chars), len(ocr_chars))
            if overlap < 0.4:
                risk_score += 25
                risk_factors.append({
                    "factor": "name_inconsistency",
                    "severity": "high",
                    "detail": f"Low name similarity ({overlap:.0%}): '{form_name}' vs '{ocr_name}'"
                })
            elif overlap < 0.7:
                risk_score += 10
                risk_factors.append({
                    "factor": "name_variation",
                    "severity": "medium",
                    "detail": f"Name partially matches ({overlap:.0%}) — possible transliteration"
                })

    # Clamp score
    risk_score = min(risk_score, 100)

    # Determine level and recommendation
    if risk_score >= 60:
        level = RiskLevel.HIGH
        recommendation = Recommendation.REJECT if risk_score >= 80 else Recommendation.MANUAL_REVIEW
    elif risk_score >= 30:
        level = RiskLevel.MEDIUM
        recommendation = Recommendation.MANUAL_REVIEW
    else:
        level = RiskLevel.LOW
        recommendation = Recommendation.AUTO_APPROVE

    return RiskAssessment(
        risk_level=level,
        risk_score=risk_score,
        risk_factors=risk_factors,
        recommendation=recommendation,
        reasoning=f"Rule-based assessment: {len(risk_factors)} risk factors identified",
        ai_generated=False,
    )


# ============================================================================
# AI-ENHANCED RISK ENGINE (Gemini)
# ============================================================================

def _ai_risk_assessment(
    ocr_data: Dict[str, Any],
    form_data: Dict[str, Any],
    quality_score: int,
    mismatches: List[Dict],
    country_code: str,
    document_type: str,
) -> Optional[RiskAssessment]:
    """
    Use Gemini to generate an AI risk assessment with reasoning.
    Returns None if Gemini is unavailable (caller uses rule-based fallback).
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""You are a KYC compliance risk analyst for Deriv, an online trading platform.
Assess the fraud and compliance risk for this document submission.

DOCUMENT INFO:
- Type: {document_type}
- Country: {country_code}
- Quality Score: {quality_score}/100

FORM DATA (user entered):
{json.dumps(form_data, indent=2, default=str)}

OCR DATA (extracted from document):
{json.dumps(ocr_data, indent=2, default=str) if ocr_data else "No data extracted"}

MISMATCHES DETECTED:
{json.dumps(mismatches, indent=2) if mismatches else "None"}

ASSESS THESE RISK FACTORS:
1. Name consistency between form and document (account for transliteration, spelling variations)
2. Document expiry status
3. Data completeness (are key fields readable?)
4. Cross-field consistency (DOB, address matches postal code region?)
5. Any fraud indicators (digital manipulation, screenshot signs, template documents)

RESPOND WITH ONLY THIS JSON:
{{
    "risk_level": "LOW" or "MEDIUM" or "HIGH",
    "risk_score": 0-100,
    "risk_factors": [
        {{"factor": "name", "severity": "low/medium/high", "detail": "explanation"}}
    ],
    "recommendation": "auto-approve" or "manual-review" or "reject",
    "reasoning": "1-2 sentence summary of your assessment"
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[genai.types.Part(text=prompt)]
        )

        text = response.text.strip()
        # Extract JSON
        if "{" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            data = json.loads(text[start:end])

            level_map = {"LOW": RiskLevel.LOW, "MEDIUM": RiskLevel.MEDIUM, "HIGH": RiskLevel.HIGH}
            rec_map = {"auto-approve": Recommendation.AUTO_APPROVE, "manual-review": Recommendation.MANUAL_REVIEW, "reject": Recommendation.REJECT}

            return RiskAssessment(
                risk_level=level_map.get(data.get("risk_level", "LOW"), RiskLevel.LOW),
                risk_score=min(int(data.get("risk_score", 0)), 100),
                risk_factors=data.get("risk_factors", []),
                recommendation=rec_map.get(data.get("recommendation", "manual-review"), Recommendation.MANUAL_REVIEW),
                reasoning=data.get("reasoning", "AI assessment complete"),
                ai_generated=True,
            )

    except Exception as e:
        logger.warning(f"[Risk Scorer] AI assessment failed: {e}")

    return None


# ============================================================================
# PUBLIC API
# ============================================================================

def assess_risk(
    ocr_data: Dict[str, Any],
    form_data: Dict[str, Any],
    quality_score: int,
    mismatches: List[Dict],
    country_code: str,
    document_type: str = "identity",
    use_ai: bool = True,
) -> RiskAssessment:
    """
    Assess the risk of a KYC document submission.

    Combines rule-based checks with optional AI analysis.
    AI enhances the assessment but rule-based always provides baseline.

    Args:
        ocr_data: Fields extracted from document via OCR
        form_data: Fields entered by user in the form
        quality_score: Document quality score (0-100)
        mismatches: List of field mismatches between form and OCR
        country_code: ISO country code
        document_type: Type of document being verified
        use_ai: Whether to attempt AI-enhanced scoring

    Returns:
        RiskAssessment with level, score, factors, and recommendation
    """
    # Always run rule-based first (fast, reliable)
    rule_result = _rule_based_risk(
        ocr_data=ocr_data,
        form_data=form_data,
        quality_score=quality_score,
        mismatches=mismatches,
        country_code=country_code,
    )

    # Try AI enhancement if enabled
    if use_ai:
        ai_result = _ai_risk_assessment(
            ocr_data=ocr_data,
            form_data=form_data,
            quality_score=quality_score,
            mismatches=mismatches,
            country_code=country_code,
            document_type=document_type,
        )

        if ai_result:
            # Merge: take the higher risk score, combine factors
            combined_factors = rule_result.risk_factors + [
                f for f in ai_result.risk_factors
                if f.get("factor") not in {rf.get("factor") for rf in rule_result.risk_factors}
            ]

            final_score = max(rule_result.risk_score, ai_result.risk_score)
            final_score = min(final_score, 100)

            if final_score >= 60:
                final_level = RiskLevel.HIGH
                final_rec = Recommendation.REJECT if final_score >= 80 else Recommendation.MANUAL_REVIEW
            elif final_score >= 30:
                final_level = RiskLevel.MEDIUM
                final_rec = Recommendation.MANUAL_REVIEW
            else:
                final_level = RiskLevel.LOW
                final_rec = Recommendation.AUTO_APPROVE

            return RiskAssessment(
                risk_level=final_level,
                risk_score=final_score,
                risk_factors=combined_factors,
                recommendation=final_rec,
                reasoning=ai_result.reasoning,
                ai_generated=True,
            )

    return rule_result
