"""Domain exceptions. External calls must wrap raw errors into these."""


class KFinGraphError(Exception):
    """Base for all K-FinGraph domain errors."""


class DartAPIError(KFinGraphError):
    """DART OpenAPI call failed or returned an error status."""


class LLMExtractionError(KFinGraphError):
    """LLM-based extraction (NER/RE) failed or produced invalid output."""


class GraphWriteError(KFinGraphError):
    """Neo4j write (MERGE/CREATE) failed."""
