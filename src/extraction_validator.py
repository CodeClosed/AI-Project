"""
Extraction Validator & Anti-Hallucination Grounding Engine for NutriMenu AI.

Cross-validates candidate menu extractions (from Vision AI) against
deterministic local OCR evidence using RapidFuzz, multi-line spanning,
culinary plausibility checks, and evidence-based calibrated confidence scoring.

Decisions:
- ACCEPT: High similarity & strong OCR evidence (grounded).
- FLAG: Moderate similarity, partial OCR evidence, or low OCR image quality (provisional).
- REJECT: Low/no OCR evidence, non-food metadata, or hallucinated text (filtered out).
"""

from typing import List, Dict, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
import logging
import re
import math
import rapidfuzz
from rapidfuzz import fuzz

from .models import TextBlock, MenuItem, MenuSection, RecognizedMenu
from .noise_filter import AdvancedNoiseFilter, is_valid_food_item
from .config import (
    DEFAULT_VALIDATOR_ACCEPT_THRESHOLD,
    DEFAULT_VALIDATOR_FLAG_THRESHOLD,
    DEFAULT_ENABLE_SECOND_PASS_VERIFICATION,
    DEFAULT_MAX_SECOND_PASS_ITEMS,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Detailed validation outcome for a single candidate menu item."""
    item_name: str
    status: str  # "accepted", "flagged", "rejected"
    confidence: float  # Calibrated 0.0 to 1.0
    best_match_text: str
    similarity_score: float  # 0.0 to 100.0
    match_strategy: str
    reason: str
    second_pass_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_name": self.item_name,
            "status": self.status,
            "confidence": round(self.confidence, 4),
            "best_match_text": self.best_match_text,
            "similarity_score": round(self.similarity_score, 2),
            "match_strategy": self.match_strategy,
            "reason": self.reason,
            "second_pass_verified": self.second_pass_verified,
        }


class ExtractionValidator:
    """
    Independent validation layer for grounding LLM extractions against local OCR evidence.
    """

    def __init__(
        self,
        accept_threshold: float = DEFAULT_VALIDATOR_ACCEPT_THRESHOLD,
        flag_threshold: float = DEFAULT_VALIDATOR_FLAG_THRESHOLD,
        enable_second_pass: bool = DEFAULT_ENABLE_SECOND_PASS_VERIFICATION,
        max_second_pass_items: int = DEFAULT_MAX_SECOND_PASS_ITEMS,
        allow_beverages: bool = False,
    ):
        self.accept_threshold = accept_threshold
        self.flag_threshold = flag_threshold
        self.enable_second_pass = enable_second_pass
        self.max_second_pass_items = max_second_pass_items
        self.allow_beverages = allow_beverages
        self.noise_filter = AdvancedNoiseFilter()

    # -------------------------------------------------------------------------
    # Step 1: Text Normalization
    # -------------------------------------------------------------------------

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Standardizes text by normalizing case, diacritics, hyphens, extra whitespace,
        punctuation, and currency symbols without destroying culinary meaning.
        """
        if not text:
            return ""

        # Convert to lowercase
        norm = text.lower()

        # Replace hyphens, underscores, slashes with single space
        norm = re.sub(r"[-_/\\|~]+", " ", norm)

        # Remove currency symbols ($, ₹, Rs, £, €, etc.)
        norm = re.sub(r"[\$\£\€\₹\¥]|rs\.?|re\.?|inr|usd|eur|gbp", " ", norm, flags=re.IGNORECASE)

        # Remove standalone digits and decimal prices (e.g., 250, 14.99, 120/-)
        norm = re.sub(r"\b\d+(?:[.,]\d{1,2})?(?:\/-)?\b", " ", norm)

        # Remove special characters / punctuation except alphanumeric and space
        norm = re.sub(r"[^\w\s]", " ", norm)

        # Collapse repeated whitespace
        norm = re.sub(r"\s+", " ", norm).strip()

        return norm

    # -------------------------------------------------------------------------
    # Step 2: OCR Evidence Extraction & Multi-Line Concatenation
    # -------------------------------------------------------------------------

    def clean_ocr_evidence(self, ocr_blocks: List[Union[TextBlock, str]]) -> List[str]:
        """
        Extracts and sanitizes text strings from raw OCR blocks.
        Filters out pure noise, contact numbers, and standalone prices.
        """
        cleaned_lines: List[str] = []
        for block in ocr_blocks:
            raw_text = block.text if isinstance(block, TextBlock) else str(block)
            if not raw_text or not raw_text.strip():
                continue

            # Strip leader dots / dashes
            line = re.sub(r"[\.·\-_]{2,}", " ", raw_text)
            norm = self.normalize_text(line)

            if norm and len(norm) >= 2:
                cleaned_lines.append(norm)

        return cleaned_lines

    @staticmethod
    def generate_multi_line_candidates(cleaned_lines: List[str], max_window: int = 3) -> List[str]:
        """
        Builds multi-line candidate strings by combining adjacent OCR lines (window 2 and 3).
        Handles food names split across lines (e.g. 'Chicken Butter' + 'Masala').
        """
        candidates: List[str] = list(cleaned_lines)
        n = len(cleaned_lines)

        # 2-line combinations
        for i in range(n - 1):
            combined_2 = f"{cleaned_lines[i]} {cleaned_lines[i + 1]}".strip()
            if combined_2:
                candidates.append(combined_2)

        # 3-line combinations
        if max_window >= 3:
            for i in range(n - 2):
                combined_3 = f"{cleaned_lines[i]} {cleaned_lines[i + 1]} {cleaned_lines[i + 2]}".strip()
                if combined_3:
                    candidates.append(combined_3)

        return candidates

    # -------------------------------------------------------------------------
    # Step 3: RapidFuzz Similarity Matching Strategy
    # -------------------------------------------------------------------------

    def calculate_similarity(self, food_name: str, ocr_candidate: str) -> Tuple[float, str]:
        """
        Calculates similarity using an adaptive combination of RapidFuzz strategies:
        - fuzz.ratio: Character-level accuracy (handles OCR typos).
        - fuzz.token_sort_ratio: Word-order invariance.
        - fuzz.token_set_ratio: Subset/superset matching with length penalty.
        - fuzz.partial_ratio: Substring matching.
        """
        norm_name = self.normalize_text(food_name)
        norm_cand = self.normalize_text(ocr_candidate)

        if not norm_name or not norm_cand:
            return 0.0, "empty"

        if norm_name == norm_cand:
            return 100.0, "exact_match"

        name_words = norm_name.split()
        cand_words = norm_cand.split()

        ratio = fuzz.ratio(norm_name, norm_cand)
        token_sort = fuzz.token_sort_ratio(norm_name, norm_cand)
        token_set = fuzz.token_set_ratio(norm_name, norm_cand)
        partial = fuzz.partial_ratio(norm_name, norm_cand)

        # Word-level overlap analysis
        name_words_set = set(name_words)
        cand_words_set = set(cand_words)
        overlap_words = name_words_set & cand_words_set
        overlap_ratio = len(overlap_words) / len(name_words) if name_words else 0.0

        len_ratio = min(len(norm_name), len(norm_cand)) / max(len(norm_name), len(norm_cand))
        word_count_ratio = min(len(name_words), len(cand_words)) / max(len(name_words), len(cand_words))

        if len(name_words) == 1:
            # Single-word items (e.g. "Mango", "Tiramisu", "Chips")
            if len(cand_words) > 3:
                effective_score = max(ratio, partial * len_ratio)
                strategy = "single_word_penalized"
            else:
                effective_score = max(ratio, token_sort, partial * 0.9)
                strategy = "single_word_direct"
        else:
            # Multi-word items (e.g. "Chicken Butter Masala")
            if all(w in cand_words for w in name_words):
                # All name words are present in candidate
                effective_score = max(token_sort, token_set * (0.80 + 0.20 * word_count_ratio), ratio)
                strategy = "multi_word_all_tokens"
            elif all(w in name_words for w in cand_words):
                # Candidate is a strict subset of name (e.g. OCR saw "Chicken Tikka" for "Chicken Tikka Masala")
                effective_score = max(ratio, token_set * overlap_ratio * 0.95)
                strategy = "multi_word_subset"
            else:
                # Disagreement / low overlap check (e.g. "Dragon Chicken Supreme" vs "Chicken Burger")
                if overlap_ratio < 0.5:
                    effective_score = min(40.0, token_sort * overlap_ratio)
                    strategy = "multi_word_low_overlap"
                else:
                    effective_score = (token_sort * 0.40) + (token_set * 0.35 * (0.7 + 0.3 * len_ratio)) + (ratio * 0.25)
                    strategy = "multi_word_composite"

        return float(min(100.0, max(0.0, effective_score))), strategy

    def find_best_ocr_match(self, food_name: str, ocr_candidates: List[str]) -> Tuple[str, float, str]:
        """
        Finds the highest-scoring matching OCR string across all candidates.
        """
        if not ocr_candidates:
            return "", 0.0, "no_candidates"

        best_cand = ""
        best_score = -1.0
        best_strategy = "none"

        for cand in ocr_candidates:
            score, strategy = self.calculate_similarity(food_name, cand)
            if score > best_score:
                best_score = score
                best_cand = cand
                best_strategy = strategy

        return best_cand, max(0.0, best_score), best_strategy

    # -------------------------------------------------------------------------
    # Step 4: OCR Quality Assessment
    # -------------------------------------------------------------------------

    @staticmethod
    def assess_ocr_quality(ocr_blocks: List[TextBlock]) -> Dict[str, Any]:
        """
        Estimates the overall readability and quality of local OCR results.
        Distinguishes between 'Item not found because hallucinated' vs 'Item not found because OCR failed'.
        """
        if not ocr_blocks:
            return {
                "quality": "DEGRADED",
                "avg_confidence": 0.0,
                "block_count": 0,
                "valid_text_count": 0,
                "is_usable": False,
            }

        confidences = [b.confidence for b in ocr_blocks if b.confidence > 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        valid_texts = [b for b in ocr_blocks if len(b.text.strip()) >= 3 and any(c.isalpha() for c in b.text)]

        block_count = len(ocr_blocks)
        valid_count = len(valid_texts)

        if block_count >= 5 and avg_conf >= 0.50 and valid_count >= 3:
            quality = "HIGH"
            is_usable = True
        elif block_count >= 2 and (avg_conf >= 0.30 or valid_count >= 2):
            quality = "MEDIUM"
            is_usable = True
        elif block_count >= 1:
            quality = "LOW"
            is_usable = True
        else:
            quality = "DEGRADED"
            is_usable = False

        return {
            "quality": quality,
            "avg_confidence": round(avg_conf, 3),
            "block_count": block_count,
            "valid_text_count": valid_count,
            "is_usable": is_usable,
        }

    # -------------------------------------------------------------------------
    # Step 5: Evidence-Based Calibrated Confidence Scoring
    # -------------------------------------------------------------------------

    def calculate_evidence_confidence(
        self,
        similarity_score: float,
        food_name: str,
        price: Optional[float] = None,
        description: Optional[str] = None,
        section: Optional[str] = None,
        ocr_quality: str = "HIGH",
    ) -> float:
        """
        Calculates calibrated confidence score (0.0 to 1.0) weighted dominantly on OCR agreement.

        Formula:
        Confidence = 0.70 * OCR_AGREEMENT
                   + (STRUCTURAL + CULINARY + OCR_CONTEXT) * (0.30 + 0.70 * OCR_AGREEMENT)
        """
        # 1. OCR Agreement (Dominant signal: 0.70 max)
        ocr_agreement = min(1.0, max(0.0, similarity_score / 100.0))

        # 2. Structural Validity (0.15 max)
        structural_score = 0.0
        if price is not None and 0.5 <= price <= 5000:
            structural_score += 0.07
        if description and len(description.strip()) >= 5:
            structural_score += 0.04
        if section and section.lower() not in ("general", "other", "unknown", ""):
            structural_score += 0.04

        # 3. Culinary Semantic Relevance (0.10 max)
        culinary_score = 0.10 if self.noise_filter.has_culinary_semantic_relevance(food_name) else 0.04

        # 4. OCR Quality Context (0.05 max)
        if ocr_quality == "HIGH":
            ocr_context = 0.05
        elif ocr_quality == "MEDIUM":
            ocr_context = 0.03
        elif ocr_quality == "LOW":
            ocr_context = 0.02
        else:  # DEGRADED
            ocr_context = 0.01

        auxiliary_signals = structural_score + culinary_score + ocr_context
        # Scale auxiliary signals by OCR agreement to prevent ungrounded items from claiming high confidence
        scaled_auxiliary = auxiliary_signals * (0.20 + 0.80 * ocr_agreement)

        total_confidence = (0.70 * ocr_agreement) + scaled_auxiliary

        # Scale to max 0.98, minimum 0.05
        return float(min(0.98, max(0.05, total_confidence)))

    # -------------------------------------------------------------------------
    # Step 6: Single Item Validation (ACCEPT / FLAG / REJECT)
    # -------------------------------------------------------------------------

    def validate_item(
        self,
        item_name: str,
        ocr_candidates: List[str],
        price: Optional[float] = None,
        description: Optional[str] = None,
        section: Optional[str] = None,
        ocr_quality: str = "HIGH",
    ) -> ValidationResult:
        """
        Validates a single candidate food item against OCR evidence.
        """
        clean_name = item_name.strip()

        # Check 1: Empty or minimal length
        if not clean_name or len(clean_name) <= 1:
            return ValidationResult(
                item_name=clean_name,
                status="rejected",
                confidence=0.0,
                best_match_text="",
                similarity_score=0.0,
                match_strategy="empty_filter",
                reason="Empty or single-character item name",
            )

        # Filter 1 & Filter 2: Deterministic food validity, template, header & beverage filter
        is_valid, invalid_reason = is_valid_food_item(clean_name, allow_beverages=self.allow_beverages)
        if not is_valid:
            logger.info(f"[VALIDATOR] Processing item: {clean_name} | Decision: REJECT ({invalid_reason})")
            return ValidationResult(
                item_name=clean_name,
                status="rejected",
                confidence=0.0,
                best_match_text="",
                similarity_score=0.0,
                match_strategy="deterministic_food_filter",
                reason=invalid_reason,
            )

        # Check 2: Obvious non-food noise (contact info, regulatory text, branding)
        if self.noise_filter.is_metadata_or_business_noise(clean_name):
            logger.info(f"[VALIDATOR] Processing item: {clean_name} | Decision: REJECT (business metadata noise)")
            return ValidationResult(
                item_name=clean_name,
                status="rejected",
                confidence=0.0,
                best_match_text="",
                similarity_score=0.0,
                match_strategy="noise_filter",
                reason="Matched non-food business/contact metadata pattern",
            )

        if self.noise_filter.is_branding_or_decorative_noise(clean_name):
            logger.info(f"[VALIDATOR] Processing item: {clean_name} | Decision: REJECT (branding/decorative noise)")
            return ValidationResult(
                item_name=clean_name,
                status="rejected",
                confidence=0.0,
                best_match_text="",
                similarity_score=0.0,
                match_strategy="branding_filter",
                reason="Matched restaurant branding or decorative noise pattern",
            )

        if self.noise_filter.is_gibberish_or_low_entropy(clean_name):
            logger.info(f"[VALIDATOR] Processing item: {clean_name} | Decision: REJECT (low entropy gibberish)")
            return ValidationResult(
                item_name=clean_name,
                status="rejected",
                confidence=0.0,
                best_match_text="",
                similarity_score=0.0,
                match_strategy="entropy_filter",
                reason="Identified as low-entropy or gibberish character sequence",
            )

        # Check 3: OCR Quality is DEGRADED (Local OCR failed completely)
        if ocr_quality == "DEGRADED" or not ocr_candidates:
            # Distinguish OCR failure from hallucination:
            # If item has culinary relevance and plausible structure, FLAG rather than REJECT
            has_culinary = self.noise_filter.has_culinary_semantic_relevance(clean_name)
            if has_culinary:
                conf = 0.60 if price is not None else 0.50
                logger.info(f"[VALIDATOR] Processing item: {clean_name} | OCR: DEGRADED | Decision: FLAG (provisional)")
                return ValidationResult(
                    item_name=clean_name,
                    status="flagged",
                    confidence=conf,
                    best_match_text="",
                    similarity_score=0.0,
                    match_strategy="ocr_degraded_fallback",
                    reason="Local OCR was unreadable; preserved provisionally based on culinary plausibility",
                )
            else:
                logger.info(f"[VALIDATOR] Processing item: {clean_name} | OCR: DEGRADED | Decision: REJECT")
                return ValidationResult(
                    item_name=clean_name,
                    status="rejected",
                    confidence=0.15,
                    best_match_text="",
                    similarity_score=0.0,
                    match_strategy="ocr_degraded_rejection",
                    reason="Local OCR was unreadable and item lacks culinary relevance",
                )

        # Check 4: Ground against OCR candidates using RapidFuzz
        best_match, similarity, strategy = self.find_best_ocr_match(clean_name, ocr_candidates)
        confidence = self.calculate_evidence_confidence(
            similarity_score=similarity,
            food_name=clean_name,
            price=price,
            description=description,
            section=section,
            ocr_quality=ocr_quality,
        )

        logger.info(
            f"[VALIDATOR] Processing item: {clean_name} | Best OCR match: '{best_match}' | Similarity: {similarity:.1f} | Strategy: {strategy}"
        )

        # Tri-State Decision Logic
        if similarity >= self.accept_threshold:
            status = "accepted"
            reason = f"Strong OCR evidence match ({similarity:.1f}% similarity)"
            logger.info(f"[VALIDATOR] Decision: ACCEPT ({reason})")
        elif similarity >= self.flag_threshold:
            status = "flagged"
            reason = f"Moderate/partial OCR evidence match ({similarity:.1f}% similarity)"
            logger.info(f"[VALIDATOR] Decision: FLAG ({reason})")
        else:
            # Low similarity
            if ocr_quality == "LOW":
                # Local OCR had low quality, so don't aggressively drop if culinary item is plausible
                if self.noise_filter.has_culinary_semantic_relevance(clean_name):
                    status = "flagged"
                    reason = f"Low OCR similarity ({similarity:.1f}%), but flagged due to low overall OCR image quality"
                    confidence = min(0.55, max(0.40, confidence))
                    logger.info(f"[VALIDATOR] Decision: FLAG ({reason})")
                else:
                    status = "rejected"
                    reason = f"Insufficient OCR evidence ({similarity:.1f}% similarity)"
                    logger.info(f"[VALIDATOR] Decision: REJECT ({reason})")
            else:
                status = "rejected"
                reason = f"Insufficient OCR evidence ({similarity:.1f}% similarity)"
                logger.info(f"[VALIDATOR] Decision: REJECT ({reason})")

        return ValidationResult(
            item_name=clean_name,
            status=status,
            confidence=confidence,
            best_match_text=best_match,
            similarity_score=similarity,
            match_strategy=strategy,
            reason=reason,
        )

    # -------------------------------------------------------------------------
    # Step 7: Batch Menu Validation & Deduplication
    # -------------------------------------------------------------------------

    def validate_menu(
        self,
        menu: RecognizedMenu,
        ocr_blocks: List[TextBlock],
        gemini_client: Optional[Any] = None,
        image_b64: Optional[str] = None,
        filter_rejected: bool = True,
    ) -> RecognizedMenu:
        """
        Cross-validates all sections and items of a RecognizedMenu against local OCR blocks.
        Updates item confidence, validation_status, ocr_match, ocr_similarity, and reason.
        Filters out rejected hallucinations while recording audit statistics in metadata.
        """
        # Assess OCR quality
        ocr_quality_meta = self.assess_ocr_quality(ocr_blocks)
        ocr_quality = ocr_quality_meta["quality"]

        # Prepare cleaned single-line and multi-line OCR candidates
        cleaned_lines = self.clean_ocr_evidence(ocr_blocks)
        ocr_candidates = self.generate_multi_line_candidates(cleaned_lines, max_window=3)

        total_evaluated = 0
        accepted_count = 0
        flagged_count = 0
        rejected_count = 0
        rejected_items_log: List[Dict[str, Any]] = []

        # Track seen normalized items for safe deduplication
        seen_normalized_items: Set[str] = set()

        validated_sections: List[MenuSection] = []

        # Validate sections
        for section in menu.sections:
            validated_items: List[MenuItem] = []

            for item in section.items:
                norm_key = self.normalize_text(item.name)
                if norm_key in seen_normalized_items:
                    logger.info(f"[VALIDATOR] Deduplicated redundant item: {item.name}")
                    continue

                total_evaluated += 1
                val_res = self.validate_item(
                    item_name=item.name,
                    ocr_candidates=ocr_candidates,
                    price=item.price,
                    description=item.description,
                    section=section.title,
                    ocr_quality=ocr_quality,
                )

                # Optional Second-Pass Verification for suspicious items
                if (
                    val_res.status == "flagged"
                    and self.enable_second_pass
                    and gemini_client
                    and image_b64
                    and rejected_count < self.max_second_pass_items
                ):
                    try:
                        second_pass_res = self._verify_item_with_gemini(
                            gemini_client=gemini_client,
                            image_b64=image_b64,
                            item_name=item.name,
                        )
                        if second_pass_res.get("visible", False):
                            val_res.status = "accepted"
                            val_res.confidence = max(val_res.confidence, float(second_pass_res.get("confidence", 0.85)))
                            val_res.second_pass_verified = True
                            val_res.reason += f" | 2nd Pass Verified: {second_pass_res.get('reason', 'Confirmed visible')}"
                        else:
                            val_res.status = "rejected"
                            val_res.reason += " | 2nd Pass Check: Confirmed NOT visible in image"
                    except Exception as e:
                        logger.warning(f"Second-pass verification failed for '{item.name}': {e}")

                # Update MenuItem metadata
                item.confidence = val_res.confidence
                item.validation_status = val_res.status
                item.ocr_match = val_res.best_match_text
                item.ocr_similarity = val_res.similarity_score
                item.validation_reason = val_res.reason

                if val_res.status == "accepted":
                    accepted_count += 1
                    seen_normalized_items.add(norm_key)
                    validated_items.append(item)
                elif val_res.status == "flagged":
                    flagged_count += 1
                    seen_normalized_items.add(norm_key)
                    validated_items.append(item)
                else:  # rejected
                    rejected_count += 1
                    rejected_items_log.append(item.to_dict())
                    if not filter_rejected:
                        validated_items.append(item)

            if validated_items:
                validated_sections.append(MenuSection(title=section.title, items=validated_items, bbox=section.bbox))

        # Validate unclassified items
        validated_unclassified: List[MenuItem] = []
        for item in menu.unclassified_items:
            norm_key = self.normalize_text(item.name)
            if norm_key in seen_normalized_items:
                continue

            total_evaluated += 1
            val_res = self.validate_item(
                item_name=item.name,
                ocr_candidates=ocr_candidates,
                price=item.price,
                description=item.description,
                section="Unclassified",
                ocr_quality=ocr_quality,
            )

            item.confidence = val_res.confidence
            item.validation_status = val_res.status
            item.ocr_match = val_res.best_match_text
            item.ocr_similarity = val_res.similarity_score
            item.validation_reason = val_res.reason

            if val_res.status in ("accepted", "flagged"):
                if val_res.status == "accepted":
                    accepted_count += 1
                else:
                    flagged_count += 1
                seen_normalized_items.add(norm_key)
                validated_unclassified.append(item)
            else:
                rejected_count += 1
                rejected_items_log.append(item.to_dict())
                if not filter_rejected:
                    validated_unclassified.append(item)

        # Update menu object
        menu.sections = validated_sections
        menu.unclassified_items = validated_unclassified
        menu.metadata["validator"] = {
            "total_evaluated": total_evaluated,
            "accepted_count": accepted_count,
            "flagged_count": flagged_count,
            "rejected_count": rejected_count,
            "ocr_quality": ocr_quality_meta,
            "accept_threshold": self.accept_threshold,
            "flag_threshold": self.flag_threshold,
            "second_pass_enabled": self.enable_second_pass,
        }
        menu.metadata["rejected_items"] = rejected_items_log

        return menu

    def _verify_item_with_gemini(
        self,
        gemini_client: Any,
        image_b64: str,
        item_name: str,
    ) -> Dict[str, Any]:
        """
        Executes a targeted, minimal second-pass verification call to check if a specific item is visible.
        Strictly forbids generating new dishes or guessing.
        """
        prompt = f"""
You are a strict menu image verification AI.
Inspect this menu image carefully.

QUESTION: Is the exact dish name '{item_name}' visibly printed anywhere on this menu image?

STRICT RULES:
1. Return ONLY valid JSON.
2. DO NOT invent new dishes.
3. DO NOT guess or infer missing words.
4. If the text '{item_name}' (or an unambiguous typo of it) is NOT clearly visible, return visible: false.

Return JSON in this format:
{{
  "item": "{item_name}",
  "visible": true,
  "confidence": 0.90,
  "reason": "Brief explanation of where/how it is visible"
}}
"""
        res = gemini_client.generate_json(
            prompt=prompt,
            image_b64=image_b64,
            temperature=0.0,
        )
        if isinstance(res, dict) and "visible" in res:
            return res
        return {"item": item_name, "visible": False, "confidence": 0.0, "reason": "Invalid response"}
