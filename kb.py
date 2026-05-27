from rapidfuzz import fuzz
from database import get_all_knowledge
from nlp_engine import SpacyNLPEngine

MATCH_THRESHOLD = 70
SPACY_SEMANTIC_THRESHOLD = 0.70


class KnowledgeBase:
    def __init__(self):
        self.nlp = SpacyNLPEngine()

    def _fetch(self):
        # Pull fresh every time so new KA entries show up without restarting.
        return get_all_knowledge()

    @staticmethod
    def _row_value(row, key, default=""):
        """
        Works with dict rows and sqlite Row-style objects.
        """
        try:
            value = row[key]
        except Exception:
            value = default
        return value or default

    def search(self, user_text: str):
        text = user_text.lower().strip()
        rows = self._fetch()

        # 1. Exact keyword match
        for row in rows:
            keyword = self._row_value(row, "keyword").lower().strip()
            if keyword and keyword in text:
                return self._row_value(row, "answer")

        # 2. Synonym match
        for row in rows:
            synonyms = self._row_value(row, "synonyms")
            if not synonyms:
                continue

            for syn in [s.strip().lower() for s in synonyms.split(",") if s.strip()]:
                if syn and syn in text:
                    return self._row_value(row, "answer")

        # 3. RapidFuzz fallback for typos / near matches
        top_score = 0
        top_answer = None

        for row in rows:
            keyword = self._row_value(row, "keyword").lower().strip()
            answer = self._row_value(row, "answer")

            if keyword:
                score = fuzz.partial_ratio(keyword, text)
                if score > top_score:
                    top_score = score
                    top_answer = answer

            synonyms = self._row_value(row, "synonyms")
            if synonyms:
                for syn in [s.strip().lower() for s in synonyms.split(",") if s.strip()]:
                    score = fuzz.partial_ratio(syn, text)
                    if score > top_score:
                        top_score = score
                        top_answer = answer

        if top_score >= MATCH_THRESHOLD:
            return top_answer

        # 4. spaCy semantic similarity fallback
        return self._semantic_search_spacy(user_text, rows)

    def _semantic_search_spacy(self, user_text: str, rows):
        """
        Semantic KB search using spaCy document similarity.

        This is used only after exact, synonym and RapidFuzz matching fail.
        It allows the chatbot to match FAQ questions that are worded differently
        from the stored keywords.
        """
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
