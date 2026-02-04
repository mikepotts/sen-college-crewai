
from dataclasses import dataclass, field
from typing import List

@dataclass
class LocationConfig:
    user_postcode: str = "LS1 1AA"
    local_radius_miles: int = 30
    local_target_count: int = 10
    local_expand_step_miles: int = 10
    local_max_radius_miles: int = 80

@dataclass
class ScoringConfig:
    w_distance: float = 0.25
    w_aspiration: float = 0.35
    w_send_fit: float = 0.40

@dataclass
class ChildContext:
    name: str = "X"
    diagnoses: List[str] = field(default_factory=lambda: ["ADHD","Autism Spectrum Condition","Global Developmental Delay"])
    needs: List[str] = field(default_factory=lambda: ["Reading support","Time management support","Visual schedules","Small groups"])
    aspirations: List[str] = field(default_factory=lambda: ["Hospitality"])

@dataclass
class RunConfig:
    location: LocationConfig = field(default_factory=LocationConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    child: ChildContext = field(default_factory=ChildContext)
    residential_preference: bool = False
