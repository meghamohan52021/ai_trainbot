from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


TRAINING_EXAMPLES = [
    #ticket
    ("i need a train ticket", "ticket"),
    ("find me the cheapest fare", "ticket"),
    ("book a return ticket", "ticket"),
    ("i want to travel from norwich to london", "ticket"),
    ("how much is a train to oxford", "ticket"),
    ("single ticket from waterloo to weymouth", "ticket"),
    ("norwich to london tomorrow morning", "ticket"),
    ("i want to go to london next friday", "ticket"),

    #delay
    ("my train is delayed", "delay"),
    ("the train is ten minutes late", "delay"),
    ("predict my arrival time", "delay"),
    ("i am at southampton and delayed fifteen minutes", "delay"),
    ("train 1w67 is late", "delay"),
    ("when will i arrive at waterloo", "delay"),

    #faq
    ("what is delay repay", "faq"),
    ("can i get a refund", "faq"),
    ("is waterloo wheelchair accessible", "faq"),
    ("can i bring a bike", "faq"),
    ("what is an advance ticket", "faq"),
    ("tell me about railcards", "faq"),

    #greeting
    ("hello", "greeting"),
    ("hi", "greeting"),
    ("hey", "greeting"),

    #goodbye
    ("bye", "goodbye"),
    ("goodbye", "goodbye"),
    ("thanks bye", "goodbye"),
]


class IntentClassifier:
    def __init__(self):
        texts, labels = zip(*TRAINING_EXAMPLES)
        self.model = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("clf", LogisticRegression(max_iter=1000))
        ])
        self.model.fit(texts, labels)

    def predict(self, text: str):
        label = self.model.predict([text])[0]
        probs = self.model.predict_proba([text])[0]
        classes = self.model.named_steps["clf"].classes_
        confidence = float(max(probs))

        return {
            "intent": label,
            "confidence": confidence,
            "scores": dict(zip(classes, map(float, probs)))
        }