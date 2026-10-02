from dataclasses import dataclass

from enums import Horizon, TargetPriority, PartyRole

@dataclass
class AIProfile:
    aggression: float = 0.5
    self_preservation: float = 0.5
    threat_weighting: float = 0.5
    tactical_horizon: Horizon = Horizon.NONE

@dataclass
class CreatureAIProfile(AIProfile):
    morale_threshold: float = 0.25
    group_morale_modifier: float = 0.0
    target_priority: TargetPriority = TargetPriority.WEAKEST

@dataclass
class PlayerAIProfile(AIProfile):
    party_role: PartyRole = PartyRole.DAMAGE
    healing_threshold: float = 0.5
    resource_conservation: float = 0.5
    nova_threshold: float = 0.25