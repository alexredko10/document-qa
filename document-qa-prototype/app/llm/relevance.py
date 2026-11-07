import re

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were",
    "what", "which", "who", "when", "where", "why",
    "how", "does", "do", "did", "can", "could",
    "many", "much", "of", "to", "in", "on", "for",
    "and", "or", "with", "have", "has", "it",
}


def content_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())

    return {
        word
        for word in words
        if word not in STOPWORDS
    }


def has_relevant_context(
    question: str,
    context: list[str],
    min_overlap: float = 0.5,
) -> bool:
    question_words = content_words(question)

    if not question_words or not context:
        return False

    context_words = content_words(" ".join(context))

    overlap = len(question_words & context_words)
    coverage = overlap / len(question_words)

    return overlap > 0 and coverage >= min_overlap