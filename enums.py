from enum import Enum, auto

class Ability(Enum):
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"

class DamageType(Enum):
    ACID = auto()
    BLUDGEONING = auto()
    COLD = auto()
    FIRE = auto()
    FORCE = auto()
    LIGHTNING = auto()
    NECROTIC = auto()
    PIERCING = auto()
    POISON = auto()
    PSYCHIC = auto()
    RADIANT = auto()
    SLASHING = auto()
    THUNDER = auto()

class AttackResult(Enum):
    MISS = auto()
    HIT = auto()
    CRIT = auto()

class ActionType(Enum):
    ATTACK = auto()
    SPELL = auto()
    MOVE = auto()
    NONE = auto()

class TargetType(Enum):
    ALLY = "Ally"
    ENEMY = "Enemy"

class RollType(Enum):
    ATTACK = auto()
    SAVE = auto()

class TargetPriority(Enum):
    NEAREST = auto()
    WEAKEST = auto()
    HIGHEST_THREAT = auto()
