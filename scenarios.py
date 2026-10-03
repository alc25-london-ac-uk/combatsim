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

def build_party(player_registry: dict, policy: Optional[Policy] = None) -> list[Combatant]:
    return [spawn(player_registry, name, policy = policy) for name in ("Fighter", "Cleric", "Wizard")]

ENCOUNTERS: dict[str, list[str]] = {
    "five_casters_with_undead": ["Priest", "Cult Fanatic", "Druid", "Acolyte", "Acolyte", "Minotaur Skeleton", "Ogre Zombie", "Wight"],
    "resistant_horde_no_casters": ["Dretch"] * 4 + ["Grick"] * 2 + ["Magmin"] * 3 + ["Minotaur Skeleton", "Wight"],
    "mage_and_priest_with_gargoyles": ["Mage", "Priest", "Gargoyle", "Gargoyle", "Skeleton"],
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
    """Every (encounter, policy name) combination, in a fixed order. The policy is always the PCs' policy: the monsters always play GreedyUtilityPolicy."""
    return [(encounter, policy_name) for encounter in ENCOUNTERS for policy_name in POLICIES]

def configuration_seed(base_seed: Optional[int], encounter: str, policy_name: str) -> Optional[int]:
    """A seed that depends only on the base seed and the configuration, never on scheduling order.

    Each configuration uses one seed above the base, so base seeds for separate runs should be at least len(configurations()) apart to avoid sharing a stream.
    """
    if base_seed is None:
        return None
    return base_seed + configurations().index((encounter, policy_name))
