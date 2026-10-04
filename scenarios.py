from typing import Optional

from combatant import Combatant
from data import spawn
from policy import Policy
from policy_random import RandomPolicy
from policy_greedyutility import GreedyUtilityPolicy
from policy_beliefupdating import BeliefUpdatingPolicy
from policy_omniscient import OmniscientPolicy

POLICIES: dict[str, type[Policy]] = {
    "Random": RandomPolicy,
    "Greedy": GreedyUtilityPolicy,
    "BeliefUpdating": BeliefUpdatingPolicy,
    "Omniscient": OmniscientPolicy,
}

PARTY: list[tuple[str, str]] = [("Fighter", "Fighter 1"), ("Fighter", "Fighter 2"), ("Cleric", "Cleric"), ("Wizard", "Wizard")] # (class, label): two Fighters, so their labels are numbered like the monsters'

def build_party(player_registry: dict, policy: Optional[Policy] = None) -> list[Combatant]:
    return [spawn(player_registry, class_name, label, policy = policy) for class_name, label in PARTY]

ENCOUNTERS: dict[str, list[str]] = {
    "priests_with_boars": ["Priest"] * 2 + ["Giant Boar"] * 7,
    "resistant_horde_no_casters": ["Dretch"] * 4 + ["Magmin"] * 3 + ["Minotaur Skeleton"] * 3 + ["Gargoyle", "Awakened Tree"],
}

def build_monsters(monster_names: list[str], monster_registry: dict, policy: Optional[Policy] = None) -> list[Combatant]:
    counts: dict[str, int] = {}
    monsters = []
    for monster_name in monster_names:
        counts[monster_name] = counts.get(monster_name, 0) + 1
        label = monster_name if monster_names.count(monster_name) == 1 else f"{monster_name} {counts[monster_name]}"
        monsters.append(spawn(monster_registry, monster_name, label, policy = policy))
    return monsters

def build_encounter(name: str, monster_registry: dict, policy: Optional[Policy] = None) -> list[Combatant]:
    return build_monsters(ENCOUNTERS[name], monster_registry, policy)

def configurations() -> list[tuple[str, str]]:
    return [(encounter, policy_name) for encounter in ENCOUNTERS for policy_name in POLICIES]

def configuration_seed(base_seed: Optional[int], encounter: str, policy_name: str) -> Optional[int]:
    if base_seed is None:
        return None
    return base_seed + configurations().index((encounter, policy_name))
