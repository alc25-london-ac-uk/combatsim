from dataclasses import dataclass

from enums import TargetPriority

@dataclass
class CreatureAIProfile:
    target_priority: TargetPriority = TargetPriority.WEAKEST
