import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from rapidfuzz import fuzz, process
except Exception:
    fuzz = None
    process = None


@dataclass
class StationCandidate:
    station: str
    score: float = 0.0


@dataclass
class StationMatch:
    status: str  #"exact", "ambiguous", "not_found"
    raw_text: str
    station: Optional[str] = None
    candidates: List[StationCandidate] = None
    score: float = 0.0
    reason: str = ""

    def __post_init__(self):
        if self.candidates is None:
            self.candidates = []
        converted = []
        for item in self.candidates:
            if isinstance(item, StationCandidate):
                converted.append(item)
            else:
                converted.append(StationCandidate(station=str(item), score=0.0))
        self.candidates = converted

    @property
    def ambiguous(self) -> bool:
        return self.status == "ambiguous"

    @property
    def query(self) -> str:
        return self.raw_text


class StationMatcher:
    # Words that commonly appear in station queries but are not part of station names, 
    #cause false matches if not filtered out

    NON_STATION_WORDS = {
        "single", "return", "yes", "no", "y", "n", "correct", "wrong",
        "time", "date", "tomorrow", "today", "morning", "afternoon",
        "evening", "night", "after", "before", "next", "day", "days",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "huh", "what", "why", "everything", "all", "please", "thanks", "thank"
    }

    FILLER_WORDS = {
        "station", "train", "rail", "the", "a", "an", "to", "from", "at", "in", "on"
    }

    def __init__(self, station_aliases: Optional[Dict[str, str]] = None, max_ngram: int = 6):
        if station_aliases is None:
            from station_data import STATION_ALIASES
            station_aliases = STATION_ALIASES

        self.station_aliases = station_aliases
        self.max_ngram = max_ngram
        self.key_to_officials: Dict[str, List[str]] = {}
        self.officials: List[str] = []
        self.official_norms: Dict[str, str] = {}
        self._build_index()

    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", str(text))
        text = text.replace("’", "'").replace("`", "'")
        text = text.replace("'", "")
        text = text.lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _dedupe(items: Iterable[str]) -> List[str]:
        seen = set()
        output = []
        for item in items:
            if item and item not in seen:
                output.append(item)
                seen.add(item)
        return output

    def _add_key(self, key: str, official: str):
        norm = self.normalize(key)
        if not norm:
            return
        self.key_to_officials.setdefault(norm, [])
        if official not in self.key_to_officials[norm]:
            self.key_to_officials[norm].append(official)

    def _build_index(self):
        officials = []
        for alias, official in self.station_aliases.items():
            if not official:
                continue
            officials.append(official)
            self._add_key(alias, official)
            self._add_key(official, official)
        self.officials = self._dedupe(officials)
        self.official_norms = {official: self.normalize(official) for official in self.officials}

    def _query_tokens(self, query_norm: str) -> List[str]:
        return [
            token for token in query_norm.split()
            if token not in self.NON_STATION_WORDS and token not in self.FILLER_WORDS
        ]

    def _is_non_station_input(self, query_norm: str) -> bool:
        tokens = query_norm.split()
        if not tokens:
            return True
        if query_norm in self.NON_STATION_WORDS:
            return True
        if all(token in self.NON_STATION_WORDS for token in tokens):
            return True
        return False

    def _strict_token_candidates(self, query_norm: str) -> List[StationCandidate]:
        #only return stations whose official or alias text contains every query token for multi token queries,
        #so “london liverpool” matches “LIVERPOOL STREET LONDON” but rejects unrelated or partial matches
        query_tokens = self._query_tokens(query_norm)
        if len(query_tokens) < 2:
            return []

        candidates: Dict[str, float] = {}

        #Search official names
        for official, norm in self.official_norms.items():
            station_tokens = set(norm.split())
            if all(token in station_tokens for token in query_tokens):
                score = 95.0
                if norm.startswith(query_norm):
                    score = 99.0
                elif query_norm in norm:
                    score = 97.0
                elif fuzz:
                    score = max(score, float(fuzz.token_set_ratio(query_norm, norm)))
                candidates[official] = max(candidates.get(official, 0.0), score)

        #search aliases too, but return official station names
        for key_norm, officials in self.key_to_officials.items():
            key_tokens = set(key_norm.split())
            if all(token in key_tokens for token in query_tokens):
                score = 96.0
                if key_norm.startswith(query_norm):
                    score = 99.0
                elif query_norm in key_norm:
                    score = 98.0
                elif fuzz:
                    score = max(score, float(fuzz.token_set_ratio(query_norm, key_norm)))
                for official in officials:
                    candidates[official] = max(candidates.get(official, 0.0), score)

        result = [StationCandidate(station=s, score=sc) for s, sc in candidates.items()]
        result.sort(key=lambda c: (-c.score, c.station))
        return result

    def _broad_candidates(self, query_norm: str) -> List[StationCandidate]:
        if not query_norm:
            return []

        query_tokens = self._query_tokens(query_norm)
        if not query_tokens:
            return []

        #multi-token queries use strict all-token filtering
        if len(query_tokens) >= 2:
            return self._strict_token_candidates(query_norm)

        token = query_tokens[0]
        candidates = []
        for official, norm in self.official_norms.items():
            station_tokens = norm.split()
            score = 0.0
            if norm == token:
                score = 100.0
            elif station_tokens and station_tokens[0] == token:
                score = 96.0
            elif token in station_tokens:
                score = 88.0
            if score > 0:
                candidates.append(StationCandidate(station=official, score=score))

        candidates.sort(key=lambda c: (-c.score, c.station))
        return candidates

    def match(self, text: str, allow_fuzzy: bool = True) -> StationMatch:
        raw = text or ""
        query_norm = self.normalize(raw)

        if not query_norm:
            return StationMatch(status="not_found", raw_text=raw, reason="empty")
        if self._is_non_station_input(query_norm):
            return StationMatch(status="not_found", raw_text=raw, reason="non_station_word")

        #Exact alias/official match from CSV-derived station data
        exact = self.key_to_officials.get(query_norm, [])
        if len(exact) == 1:
            return StationMatch(status="exact", raw_text=raw, station=exact[0], score=100.0, reason="exact")
        if len(exact) > 1:
            return StationMatch(
                status="ambiguous",
                raw_text=raw,
                candidates=[StationCandidate(s, 100.0) for s in exact[:8]],
                reason="exact_multiple",
            )

        #token search
        broad = self._broad_candidates(query_norm)
        if len(broad) == 1 and broad[0].score >= 94:
            return StationMatch(
                status="exact",
                raw_text=raw,
                station=broad[0].station,
                candidates=broad,
                score=broad[0].score,
                reason="single_token_candidate",
            )
        if len(broad) > 1:
            return StationMatch(
                status="ambiguous",
                raw_text=raw,
                candidates=broad[:8],
                score=broad[0].score,
                reason="broad_or_strict_candidates",
            )

        #Fuzzy matching ONLY for one-token typo correction.
        #Multi-word queries already used strict all-token matching to prevent unrelated fuzzy matches.
        query_tokens = self._query_tokens(query_norm)
        if allow_fuzzy and process and len(query_tokens) == 1 and len(query_norm) >= 4:
            keys = list(self.key_to_officials.keys())
            results = process.extract(query_norm, keys, scorer=fuzz.WRatio, limit=6)
            candidates = []
            seen = set()
            for key, score, _ in results:
                if score < 90:
                    continue
                for official in self.key_to_officials.get(key, []):
                    if official not in seen:
                        candidates.append(StationCandidate(station=official, score=float(score)))
                        seen.add(official)
            candidates.sort(key=lambda c: (-c.score, c.station))

            if len(candidates) == 1:
                return StationMatch(
                    status="exact",
                    raw_text=raw,
                    station=candidates[0].station,
                    candidates=candidates,
                    score=candidates[0].score,
                    reason="fuzzy_single_token",
                )
            if len(candidates) > 1:
                top = candidates[0]
                second = candidates[1]
                if top.score - second.score >= 8:
                    return StationMatch(
                        status="exact",
                        raw_text=raw,
                        station=top.station,
                        candidates=candidates,
                        score=top.score,
                        reason="fuzzy_clear_winner",
                    )
                return StationMatch(
                    status="ambiguous",
                    raw_text=raw,
                    candidates=candidates[:8],
                    score=top.score,
                    reason="fuzzy_multiple",
                )

        return StationMatch(status="not_found", raw_text=raw, reason="not_found")

    def find_all(self, text: str) -> List[str]:
        norm = self.normalize(text)
        tokens = norm.split()
        found = []
        used_ranges: List[Tuple[int, int]] = []

        for n in range(min(self.max_ngram, len(tokens)), 0, -1):
            for i in range(0, len(tokens) - n + 1):
                j = i + n
                if any(not (j <= a or i >= b) for a, b in used_ranges):
                    continue
                phrase = " ".join(tokens[i:j])
                match = self.match(phrase, allow_fuzzy=False)
                if match.status == "exact" and match.station and match.station not in found:
                    found.append(match.station)
                    used_ranges.append((i, j))
        return found
