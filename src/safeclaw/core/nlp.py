"""
SafeClaw NLP - Named Entity Recognition using spaCy.

ML without LLMs - runs locally.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# spaCy
try:
    import spacy
    HAS_SPACY = True
except ImportError:
    HAS_SPACY = False


@dataclass
class Entity:
    """A named entity."""
    text: str
    label: str
    start: int
    end: int


@dataclass
class NLPResult:
    """NLP analysis result."""
    entities: list[str] | None = None  # type: ignore
    sentences: list[str] | None = None  # type: ignore
    language: str | None = None


class NLPProcessor:
    """spaCy-based NLP processor."""

    def __init__(self, model: str = "en_core_web_sm"):
        """
        Initialize NLP.

        Args:
            model: spaCy model name
        """
        self._model = None
        self._model_name = model
        if HAS_SPACY:
            self._load_model()

    def _load_model(self) -> bool:
        try:
            if not spacy.util.is_package(self._model_name):
                logger.warning(f"spaCy model {self._model_name} not found. Attempting download...")
                spacy.cli.download(self._model_name)  # type: ignore

            self._model = spacy.load(self._model_name)
            logger.info(f"Loaded spaCy model: {self._model_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load spaCy: {e}")
            return False

    @property
    def is_available(self) -> bool:
        return HAS_SPACY and self._model is not None

    def analyze(self, text: str) -> NLPResult:
        """
        Analyze text.

        Args:
            text: Input text
        """
        if not self.is_available:
            return NLPResult()

        try:
            doc = self._model(text)  # type: ignore

            entities = [
                f"{ent.text} ({ent.label_})"
                for ent in doc.ents
            ]

            sentences = [
                sent.text.strip()
                for sent in doc.sents
            ]

            return NLPResult(
                entities=entities,
                sentences=sentences,
                language=doc.lang_,
            )
        except Exception as e:
            logger.error(f"NLP analysis failed: {e}")
            return NLPResult()

    def extract_entities(self, text: str, labels: list[str] | None = None) -> list[str]:
        """Extract specific entities."""
        if not self.is_available:
            return []

        try:
            doc = self._model(text)  # type: ignore
            entities = []

            for ent in doc.ents:
                if labels and ent.label_ not in labels:
                    continue
                entities.append(ent.text)

            return entities
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
