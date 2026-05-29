from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Tuple

import spacy
from rapidfuzz import fuzz


@dataclass
class NLPAnalysis:
    original_text: str
    cleaned_text: str
    tokens: List[str]
    lemmas: List[str]
    entities: List[Tuple[str, str]]
    noun_chunks: List[str]


@lru_cache(maxsize=1)
def load_spacy_model():
    """
    Load a spaCy English model.

    en_core_web_md is preferred because it includes word vectors for better
    semantic similarity. If it is not installed, the code falls back to
    en_core_web_sm. The small model is still useful for tokenisation,
    lemmatisation and entity extraction, but semantic similarity is weaker.
    """
    try:
        return spacy.load("en_core_web_md")
    except OSError:
        try:
            return spacy.load("en_core_web_sm")
        except OSError as exc:
            raise RuntimeError(
                "No spaCy English model found. Run:\n"
                "python -m spacy download en_core_web_md"
            ) from exc


class SpacyNLPEngine:
    def __init__(self):
        self.nlp = load_spacy_model()

    def clean_text(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def analyse(self, text: str) -> NLPAnalysis:
        cleaned = self.clean_text(text)
        doc = self.nlp(cleaned)

        tokens = [
            token.text.lower()
            for token in doc
            if not token.is_space and not token.is_punct
        ]

        lemmas = [
            token.lemma_.lower()
            for token in doc
            if not token.is_space
            and not token.is_punct
            and not token.is_stop
        ]

        entities = [(ent.text, ent.label_) for ent in doc.ents]

        try:
            noun_chunks = [chunk.text for chunk in doc.noun_chunks]
        except Exception:
            noun_chunks = []

        return NLPAnalysis(
            original_text=text,
            cleaned_text=cleaned,
            tokens=tokens,
            lemmas=lemmas,
            entities=entities,
            noun_chunks=noun_chunks,
        )

    def similarity(self, text_a: str, text_b: str) -> float:
        """
        Semantic similarity using spaCy document vectors.

        This works best with en_core_web_md. If vectors are unavailable,
        the method falls back to RapidFuzz token-set similarity so the KB
        search still works instead of returning zero for every item.
        """
        doc_a = self.nlp(text_a)
        doc_b = self.nlp(text_b)

        if doc_a.vector_norm and doc_b.vector_norm:
            return float(doc_a.similarity(doc_b))

        return fuzz.token_set_ratio(text_a.lower(), text_b.lower()) / 100.0

    def best_similarity_match(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.65,
    ) -> Tuple[Optional[str], float]:
        best_text = None
        best_score = 0.0

        for candidate in candidates:
            score = self.similarity(query, candidate)
            if score > best_score:
                best_text = candidate
                best_score = score

        if best_score >= threshold:
            return best_text, best_score

        return None, best_score

    def contains_fuzzy_term(self, text: str, terms: set[str], threshold: int = 84) -> bool:
        """
        Detect misspelled trigger terms such as 'dalayyyed' ≈ 'delayed'.
        This is only used for short intent trigger words, not station matching.
        """
        analysis = self.analyse(text)
        words = analysis.tokens + analysis.lemmas

        for word in words:
            for term in terms:
                if word == term or fuzz.ratio(word, term) >= threshold:
                    return True
        return False

    def has_delay_language(self, text: str) -> bool:
        """
        Detect delay intent using spaCy tokens/lemmas plus fuzzy matching.
        Examples: delayed, delay, late, lateness, running late, dalayyyed.
        """
        delay_terms = {
            "delay", "delayed", "late", "lateness", "arrival", "arrive",
            "reached", "current", "minutes", "mins",
        }
        return self.contains_fuzzy_term(text, delay_terms, threshold=82)

    def has_ticket_language(self, text: str) -> bool:
        """
        Detect ticket/journey language using spaCy tokens/lemmas.
        """
        ticket_terms = {
            "ticket", "fare", "price", "cheap", "cheapest", "book", "booking",
            "travel", "journey", "train", "return", "single",
        }
        return self.contains_fuzzy_term(text, ticket_terms, threshold=88)
