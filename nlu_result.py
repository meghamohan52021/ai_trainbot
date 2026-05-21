from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class NLUResult:
    intent: str = "unknown"
    intent_confidence: float = 0.0
    entities: Dict[str, Any] = field(default_factory=dict)
    entity_confidence: Dict[str, float] = field(default_factory=dict)
    source: str = "rules"
    needs_llm_fallback: bool = False
    raw_text: Optional[str] = None