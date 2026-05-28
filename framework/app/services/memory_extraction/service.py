"""
Memory Extraction Service
Extracts key information from conversation history
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ExtractedMemory:
    """Extracted memory item"""
    category: str
    content: str
    confidence: float
    source_turn: int


class MemoryExtractionService:
    """
    Extracts key information from conversation history.
    Used for building long-term knowledge bases.
    """

    def __init__(self):
        self._extractors: Dict[str, callable] = {}

    def register_extractor(self, category: str, extractor: callable) -> None:
        """Register an extractor for a category"""
        self._extractors[category] = extractor

    async def extract(
        self,
        messages: List[Dict[str, Any]],
        categories: Optional[List[str]] = None
    ) -> List[ExtractedMemory]:
        """
        Extract memories from messages.
        """
        if categories is None:
            categories = list(self._extractors.keys())

        memories = []
        for category in categories:
            extractor = self._extractors.get(category)
            if extractor:
                extracted = await extractor(messages)
                memories.extend(extracted)

        return memories

    async def extract_entities(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[ExtractedMemory]:
        """Extract named entities"""
        # Placeholder - would use NER
        return []

    async def extract_facts(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[ExtractedMemory]:
        """Extract factual information"""
        # Placeholder - would use fact extraction
        return []

    async def extract_user_preferences(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[ExtractedMemory]:
        """Extract user preferences"""
        # Placeholder
        return []


# Global extraction service
_extraction_service: Optional[MemoryExtractionService] = None


def get_extraction_service() -> MemoryExtractionService:
    """Get the global extraction service"""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = MemoryExtractionService()
    return _extraction_service