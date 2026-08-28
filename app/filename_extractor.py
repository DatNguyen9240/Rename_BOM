"""
Filename and code extraction engine with regex, heuristics, and OCR disambiguation.
"""

import re
from typing import List, Tuple, Optional, Set
from app.config import AppConfig
from app.models import CandidateMatch


class FilenameExtractor:
    """Extracts, normalizes, and ranks candidate filenames/codes from OCR results."""

    def __init__(self, config: AppConfig):
        self.config = config

    def detect_bom_type(
        self, ocr_results: List[Tuple[List[List[float]], str, float]]
    ) -> str:
        """
        Classifies engineering document header into 'BOM 1' or 'BOM 2'.
        - If document specifies BOM2 / (BOM2) / 产品(BOM2) -> 'BOM 2'
        - If document specifies BOM / (BOM) / BOM1 / 产品(BOM) -> 'BOM 1' (Mặc định nếu là BOM thì là BOM1)
        """
        if not ocr_results:
            return "BOM 1"

        texts = [raw_text.upper().strip() for _, raw_text, _ in ocr_results if raw_text]
        combined = " ".join(texts)

        # 1. Kiểm tra BOM2 trước (BOM2, (BOM2), （BOM2）)
        if re.search(r"\(BOM\s*2\)|BOM\s*2|BOM2|（BOM2）", combined):
            return "BOM 2"

        # 2. Nếu có chữ BOM hoặc (BOM) -> chắc chắn là BOM 1
        if "BOM" in combined:
            return "BOM 1"

        # Mặc định tài liệu kỹ thuật bản vẽ
        return "BOM 1"

    def extract_candidates(
        self, ocr_results: List[Tuple[List[List[float]], str, float]]
    ) -> List[CandidateMatch]:
        """
        Processes raw OCR line detections into a ranked list of candidate codes.
        ocr_results: List of (box, text, confidence)
        """
        candidates: List[CandidateMatch] = []
        seen_codes: Set[str] = set()

        compiled_regex = self._get_compiled_regex()

        for box, raw_text, conf in ocr_results:
            if not raw_text or conf < 0.1:
                continue

            cleaned_text = raw_text.strip()
            # Normalize all Unicode dash/hyphen variants to standard ASCII '-'
            cleaned_text = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uff0d]", "-", cleaned_text)
            # Remove redundant internal spaces around hyphens: 'CTIM21 - 04' -> 'CTIM21-04'
            cleaned_text = re.sub(r"\s*-\s*", "-", cleaned_text)

            # 1. Try finding candidates in the raw text directly
            matches = self._find_matches_in_text(cleaned_text, compiled_regex)

            # 2. Try Heuristic Disambiguation if enabled and no direct match
            corrected_text, is_corrected, corr_details = self._apply_disambiguation(cleaned_text)
            if is_corrected:
                corr_matches = self._find_matches_in_text(corrected_text, compiled_regex)
                for code in corr_matches:
                    if code not in seen_codes:
                        score = self._calculate_score(code, conf, is_perfect_token=(code == corrected_text), is_corrected=True)
                        cand = CandidateMatch(
                            code=self._format_code(code),
                            confidence=conf,
                            raw_text=raw_text,
                            box_coords=box,
                            is_corrected=True,
                            correction_details=corr_details,
                            score=score,
                        )
                        candidates.append(cand)
                        seen_codes.add(code)

            for code in matches:
                if code not in seen_codes:
                    score = self._calculate_score(
                        code, conf, is_perfect_token=(code == cleaned_text), is_corrected=False, raw_context=raw_text
                    )
                    cand = CandidateMatch(
                        code=self._format_code(code),
                        confidence=conf,
                        raw_text=raw_text,
                        box_coords=box,
                        is_corrected=False,
                        correction_details="",
                        score=score,
                    )
                    candidates.append(cand)
                    seen_codes.add(code)

        # Sort candidates: Highest score first, then highest confidence
        candidates.sort(key=lambda c: (c.score, c.confidence), reverse=True)
        return candidates

    def _get_compiled_regex(self) -> Optional[re.Pattern]:
        """Compiles user regex or builds pattern based on extraction mode."""
        pattern_str = self.config.regex_pattern.strip()
        if not pattern_str:
            pattern_str = r"[A-Za-z0-9_-]+"

        try:
            return re.compile(pattern_str, re.IGNORECASE)
        except re.error as e:
            print(f"[FilenameExtractor] Invalid regex pattern '{pattern_str}': {e}. Falling back.")
            return re.compile(r"[A-Za-z0-9_-]+", re.IGNORECASE)

    def _find_matches_in_text(self, text: str, regex: Optional[re.Pattern]) -> List[str]:
        """Finds all candidate strings in text conforming to length and pattern constraints."""
        found: List[str] = []
        if not text or not regex:
            return found

        # Approach 1: Regex finditer on text
        for match in regex.finditer(text):
            val = match.group(0).strip()
            if self._is_valid_length(val):
                found.append(val)

        # Approach 2: Tokenize by common delimiters (:, -, _, space, #)
        tokens = re.split(r"[\s:;,\t#\(\)\[\]{}]+", text)
        for token in tokens:
            token_clean = token.strip()
            if not token_clean:
                continue
            if regex.fullmatch(token_clean) and self._is_valid_length(token_clean):
                if token_clean not in found:
                    found.append(token_clean)

        return found

    def _is_valid_length(self, code: str) -> bool:
        """Validates minimum and maximum length constraints."""
        length = len(code)
        return self.config.min_length <= length <= self.config.max_length

    def _apply_disambiguation(self, text: str) -> Tuple[str, bool, str]:
        """
        Applies smart character disambiguation (O->0, I->1, S->5, etc.)
        when evidence indicates numbers/codes.
        """
        if not self.config.enable_disambiguation:
            return text, False, ""

        mod_chars = []
        changes = []
        is_digit_heavy = sum(c.isdigit() for c in text) >= (len(text) * 0.4)

        for i, char in enumerate(text):
            # Context-aware replacement: if surrounding characters are digits or code-like
            prev_is_digit = (i > 0 and (text[i - 1].isdigit() or text[i - 1] in ('B', 'O', 'S')))
            next_is_digit = (i < len(text) - 1 and (text[i + 1].isdigit() or text[i + 1] in ('B', 'O', 'S')))
            surrounded_by_digits = prev_is_digit or next_is_digit or is_digit_heavy or (i < 4 and len(text) >= 8)

            if self.config.correct_o_to_zero and char in ('O', 'o') and surrounded_by_digits:
                mod_chars.append('0')
                changes.append(f"{char}→0")
            elif self.config.correct_i_to_one and char in ('I', 'l', '|') and (surrounded_by_digits or (i > 0 and i < 3)):
                mod_chars.append('1')
                changes.append(f"{char}→1")
            elif self.config.correct_s_to_five and char in ('S', 's') and (surrounded_by_digits or (i > 0 and text[i-1] in ('0', '8', 'B'))):
                mod_chars.append('5')
                changes.append(f"{char}→5")
            elif self.config.correct_b_to_eight and char == 'B' and (surrounded_by_digits or i == 0):
                mod_chars.append('8')
                changes.append(f"{char}→8")
            elif self.config.correct_z_to_two and char in ('Z', 'z') and surrounded_by_digits:
                mod_chars.append('2')
                changes.append(f"{char}→2")
            else:
                mod_chars.append(char)

        if changes:
            return "".join(mod_chars), True, ", ".join(changes)
        return text, False, ""

    def _calculate_score(
        self,
        code: str,
        confidence: float,
        is_perfect_token: bool,
        is_corrected: bool,
        raw_context: str = "",
    ) -> float:
        """Calculates a ranking score for candidates with label anchor bonus."""
        score = confidence * 50.0

        # Exact token match bonus
        if is_perfect_token:
            score += 20.0

        # Length score (longer specific identifiers generally have higher priority)
        score += min(len(code) * 2.0, 20.0)

        # Keyword Context Bonus (Labels like SỐ BV, CHENKAI, BOM, VCK, MÃ SỐ)
        context_upper = (raw_context or "").upper()
        anchor_keywords = ["BV", "CHENKAI", "VCK", "BOM", "SỐ", "MÃ", "PART", "DRAWING"]
        if any(kw in context_upper for kw in anchor_keywords):
            score += 30.0

        # Bonus for drawing number format with hyphen (e.g., -04, -01)
        if re.search(r"-[0-9]{2}\b", code):
            score += 25.0

        # Penalize if it contains only generic words or is too short
        if len(code) < 3:
            score -= 15.0

        # Slight penalty for corrected strings compared to exact OCR matches
        if is_corrected:
            score -= 3.0

        return score

    def _format_code(self, code: str) -> str:
        """Applies prefix, suffix and casing format + drawing number prefix normalization."""
        formatted = code.strip()

        # Deterministic correction for drawing numbers (B0S8991 -> 8058991, BOS8991 -> 8058991, 8OS8991 -> 8058991, B018991 -> 8018991)
        if re.match(r"^[Bb][0Oo][Ss5]\d+", formatted):
            formatted = "805" + formatted[3:]
        elif re.match(r"^8[0Oo][Ss]\d+", formatted):
            formatted = "805" + formatted[3:]
        elif re.match(r"^[Bb][0Oo]\d+", formatted):
            formatted = "80" + formatted[2:]
        elif re.match(r"^8[0Oo]\d+", formatted):
            formatted = "80" + formatted[2:]
        elif re.match(r"^[Bb]\d{6,}", formatted):
            formatted = "8" + formatted[1:]

        if self.config.case_format == "UPPER":
            formatted = formatted.upper()
        elif self.config.case_format == "LOWER":
            formatted = formatted.lower()

        # Sanitize characters not allowed in Windows filenames
        formatted = re.sub(r'[\\/*?:"<>|]', '_', formatted)
        return formatted
