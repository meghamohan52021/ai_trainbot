from rapidfuzz import fuzz
from database import get_all_knowledge

# Fuzzy match threshold — how similar the user's text needs to be to a keyword
# to count as a match. 70 is forgiving enough for typos and paraphrasing.
FUZZY_THRESHOLD = 70


class KnowledgeBase:
    """
    Reads domain knowledge from the SQLite database.

    Matching works in three layers, tried in order:
    1. Exact keyword match — fastest, catches direct hits.
    2. Synonym match — catches paraphrases like "senior card" -> railcard.
    3. Fuzzy match — catches typos and near-matches using token ratio scoring.

    Any layer returning a match above the threshold wins and returns immediately.
    """

    def _load_entries(self) -> list:
        """
        Fetches all knowledge entries fresh from the DB each call.
        This means newly added KA entries are immediately available
        without restarting the chatbot.
        """
        return get_all_knowledge()

    def search(self, user_text: str):
        text = user_text.lower().strip()
        entries = self._load_entries()

        # Layer 1: exact keyword match
        for entry in entries:
            if entry["keyword"] in text:
                return entry["answer"]

        # Layer 2: synonym match
        for entry in entries:
            if not entry["synonyms"]:
                continue
            synonyms = [s.strip() for s in entry["synonyms"].split(",") if s.strip()]
            for synonym in synonyms:
                if synonym in text:
                    return entry["answer"]

        # Layer 3: fuzzy match against keyword and all synonyms
        best_score = 0
        best_answer = None

        for entry in entries:
            # Score against keyword
            score = fuzz.partial_ratio(entry["keyword"], text)
            if score > best_score:
                best_score = score
                best_answer = entry["answer"]

            # Score against each synonym
            if entry["synonyms"]:
                synonyms = [s.strip() for s in entry["synonyms"].split(",") if s.strip()]
                for synonym in synonyms:
                    score = fuzz.partial_ratio(synonym, text)
                    if score > best_score:
                        best_score = score
                        best_answer = entry["answer"]

        if best_score >= FUZZY_THRESHOLD:
            return best_answer

        return None