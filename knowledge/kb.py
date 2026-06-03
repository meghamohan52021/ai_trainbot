from rapidfuzz import fuzz
from knowledge.database import get_all_knowledge
from nlp.nlp_engine import SpacyNLPEngine

MATCH_THRESHOLD = 80
SPACY_SEMANTIC_THRESHOLD = 0.70

FAQ_KEYWORDS = {
    "delay repay", "railcard", "rail card", "refund", "split ticket", "split ticketing",
    "season ticket", "anytime", "off peak", "advance", "first class", "e-ticket",
    "wheelchair", "accessibility", "lost property", "national rail", "south western",
    "compensation", "cancelled", "peak time", "off-peak"
}


class KnowledgeBase:

    def __init__(self):
        self.nlp = SpacyNLPEngine()

    def _fetch(self):
        return get_all_knowledge()

    @staticmethod
    def _row_value(row, key, default=""):
        try:
            value = row[key]
        except Exception:
            value = default
        return value or default

    def _looks_like_journey_query(self, text: str) -> bool:
        lower = text.lower().strip()
        words = lower.split()
        if len(words) > 3 and " to " in lower:
            return True
        journey_starters = ["from ", "go to ", "travel to ", "i want to go", "get me to"]
        if any(lower.startswith(s) or s in lower for s in journey_starters):
            if " to " in lower or any(w in lower for w in ["from", "travel", "journey"]):
                return True
        return False

    def _is_clear_faq(self, text: str) -> bool:
        lower = text.lower().strip()
        return any(kw in lower for kw in FAQ_KEYWORDS)

    def search(self, user_text: str):
        text = user_text.lower().strip()
        rows = self._fetch()

        for row in rows:
            keyword = self._row_value(row, "keyword").lower().strip()
            if keyword and keyword in text:
                return self._row_value(row, "answer")

        for row in rows:
            synonyms = self._row_value(row, "synonyms")
            if not synonyms:
                continue
            for syn in [s.strip().lower() for s in synonyms.split(",") if s.strip()]:
                if syn and syn in text:
                    return self._row_value(row, "answer")

        if self._looks_like_journey_query(text) and not self._is_clear_faq(text):
            return None

        top_score = 0
        top_answer = None
        for row in rows:
            keyword = self._row_value(row, "keyword").lower().strip()
            answer = self._row_value(row, "answer")
            if keyword:
                score = fuzz.ratio(keyword, text)
                if score > top_score:
                    top_score = score
                    top_answer = answer
            synonyms = self._row_value(row, "synonyms")
            if synonyms:
                for syn in [s.strip().lower() for s in synonyms.split(",") if s.strip()]:
                    score = fuzz.ratio(syn, text)
                    if score > top_score:
                        top_score = score
                        top_answer = answer

        if top_score >= MATCH_THRESHOLD:
            return top_answer

        return self._semantic_search_spacy(user_text, rows)

    def _semantic_search_spacy(self, user_text: str, rows):
        best_answer = None
        best_score = 0.0
        for row in rows:
            keyword = self._row_value(row, "keyword")
            synonyms = self._row_value(row, "synonyms")
            answer = self._row_value(row, "answer")
            searchable_text = " ".join(
                part for part in [keyword, synonyms, answer] if part
            )
            if not searchable_text:
                continue
            score = self.nlp.similarity(user_text, searchable_text)
            if score > best_score:
                best_score = score
                best_answer = answer
        if best_score >= SPACY_SEMANTIC_THRESHOLD:
            return best_answer
        return None