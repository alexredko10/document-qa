import re
import unicodedata


def clean_text(text: str) -> str:
    # Normalize Unicode
    text = unicodedata.normalize("NFC", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace non-breaking spaces
    text = text.replace("\u00a0", " ")

    # Remove invisible formatting characters
    text = text.replace("\u200b", "").replace("\ufeff", "")

    # Remove trailing whitespace
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

    # Reduce excessive empty lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()