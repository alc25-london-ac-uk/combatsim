from weapon import MeleeWeapon, RangedWeapon
from enums import DamageType

def test_melee_weapon_range_is_its_reach():
    sword = MeleeWeapon(name = "Longsword", damage_dice = 1, damage_sides = 10, damage_type = DamageType.SLASHING, reach = 5, finesse = False)
    assert sword.range == 5

def test_reach_weapon_has_a_longer_range():
    spear = MeleeWeapon(name = "Reach Spear", damage_dice = 1, damage_sides = 6, damage_type = DamageType.PIERCING, reach = 10, finesse = False)
    assert spear.range == 10

def test_ranged_weapon_range_is_its_maximum_distance_not_optimal_distance():
    bow = RangedWeapon(name = "Longbow", damage_dice = 1, damage_sides = 8, damage_type = DamageType.PIERCING, optimal_distance = 150, maximum_distance = 600)
    assert bow.range == 600

def test_melee_weapon_defaults_to_not_off_hand():
    sword = MeleeWeapon(name = "Longsword", damage_dice = 1, damage_sides = 10, damage_type = DamageType.SLASHING, reach = 5, finesse = False)
    assert sword.is_off_hand is False

def test_melee_weapon_can_be_flagged_off_hand():
    dagger = MeleeWeapon(name = "Dagger", damage_dice = 1, damage_sides = 4, damage_type = DamageType.PIERCING, reach = 5, finesse = True, is_off_hand = True)
    assert dagger.is_off_hand is True
