from rapidfuzz import fuzz
from database import get_all_knowledge

MATCH_THRESHOLD = 70


class KnowledgeBase:
    def _fetch(self):
        # pull fresh every time so new KA entries show up without restarting
        return get_all_knowledge()

    def search(self, user_text: str):
        text = user_text.lower().strip()
        rows = self._fetch()

        for row in rows:
            if row["keyword"] in text:
                return row["answer"]

        for row in rows:
            if not row["synonyms"]:
                continue
            for syn in [s.strip() for s in row["synonyms"].split(",") if s.strip()]:
                if syn in text:
                    return row["answer"]

        # fuzzy fallback for typos / paraphrasing
        top_score = 0
        top_answer = None
        for row in rows:
            score = fuzz.partial_ratio(row["keyword"], text)
            if score > top_score:
                top_score = score
                top_answer = row["answer"]
            if row["synonyms"]:
                for syn in [s.strip() for s in row["synonyms"].split(",") if s.strip()]:
                    score = fuzz.partial_ratio(syn, text)
                    if score > top_score:
                        top_score = score
                        top_answer = row["answer"]

        return top_answer if top_score >= MATCH_THRESHOLD else None
