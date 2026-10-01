from enums import DamageType
from combatant import AbilityScores, PlayerCharacter, Monster
from effects import Blind

# --- AbilityScores ---

def test_ability_modifier_for_average_score_is_zero():
    scores = AbilityScores(strength = 10)
    assert scores.str_mod == 0

def test_ability_modifier_rounds_down_for_odd_scores():
    scores = AbilityScores(strength = 15) # (15-10)//2 = 2 (not 2.5)
    assert scores.str_mod == 2

def test_ability_modifier_can_be_negative():
    scores = AbilityScores(strength = 6) # (6-10)//2 = -2
    assert scores.str_mod == -2

def test_modifier_for_reads_the_correct_ability_by_name():
    scores = AbilityScores(strength = 16, wisdom = 8)
    from enums import Ability
    assert scores.modifier_for(Ability.STRENGTH) == 3
    assert scores.modifier_for(Ability.WISDOM) == -1

# --- PlayerCharacter.max_hp ---

def test_fighter_max_hp_at_level_one_is_hit_die_plus_con_mod(make_player):
    fighter = make_player(character_class = "fighter", level = 1)
    con_mod = fighter.ability_scores.con_mod
    assert fighter.max_hp == 10 + con_mod

def test_max_hp_scales_with_level(make_player):
    level_1 = make_player(character_class = "fighter", level = 1)
    level_5 = make_player(character_class = "fighter", level = 5)
    assert level_5.max_hp > level_1.max_hp

def test_cleric_and_rogue_share_the_same_hit_dice(make_player):
    cleric = make_player(character_class = "cleric", level = 3)
    rogue = make_player(character_class = "rogue", level = 3)
    assert cleric.max_hp == rogue.max_hp

# --- proficiency_bonus / caster_level ---

def test_proficiency_bonus_increases_every_four_levels(make_player):
    assert make_player(level = 1).proficiency_bonus == 2
    assert make_player(level = 4).proficiency_bonus == 2
    assert make_player(level = 5).proficiency_bonus == 3
    assert make_player(level = 9).proficiency_bonus == 4

def test_player_caster_level_is_character_level(make_player):
    player = make_player(level = 7)
    assert player.caster_level == 7

def test_monster_caster_level_defaults_to_zero_and_can_be_set(make_monster):
    goblin = make_monster()
    assert goblin.caster_level == 0

    lich = make_monster(spellcaster_level = 18)
    assert lich.caster_level == 18

# --- get_damage_bonus ---

def test_non_finesse_melee_weapon_uses_strength(make_player, melee_weapon):
    player = make_player()
    player.ability_scores.strength = 16
    player.ability_scores.dexterity = 20
    weapon = melee_weapon(finesse = False)
    assert player.get_damage_bonus(weapon) == player.ability_scores.str_mod

def test_finesse_melee_weapon_uses_dexterity(make_player, melee_weapon):
    player = make_player()
    player.ability_scores.strength = 16
    player.ability_scores.dexterity = 20
    weapon = melee_weapon(finesse = True)
    assert player.get_damage_bonus(weapon) == player.ability_scores.dex_mod

def test_ranged_weapon_always_uses_dexterity(make_player, ranged_weapon):
    player = make_player()
    player.ability_scores.strength = 20
    player.ability_scores.dexterity = 16
    weapon = ranged_weapon()
    assert player.get_damage_bonus(weapon) == player.ability_scores.dex_mod

# --- fighter extra attack ---

def test_fighter_gets_extra_attack_at_level_five(make_player):
    assert make_player(character_class = "fighter", level = 4).attack_count == 1
    assert make_player(character_class = "fighter", level = 5).attack_count == 2

def test_non_fighters_do_not_get_extra_attack(make_player):
    assert make_player(character_class = "cleric", level = 5).attack_count == 1

# --- effect lifecycle: add/remove/has_effect and the on_apply/on_remove hooks ---

def test_add_effect_fires_on_apply(make_player):
    player = make_player(ac = 12)
    from effects import Barkskin
    player.add_effect(Barkskin())
    assert player.ac == 16 # Barkskin's on_apply raises AC to a minimum of 16

def test_remove_effect_fires_on_remove(make_player):
    player = make_player(ac = 12)
    from effects import Barkskin
    barkskin = Barkskin()
    player.add_effect(barkskin)
    player.remove_effect(barkskin)
    assert player.ac == 12 # restored by Barkskin's on_remove

def test_has_effect_checks_by_type(make_player):
    player = make_player()
    assert player.has_effect(Blind) is False
    player.add_effect(Blind())
    assert player.has_effect(Blind) is True

# --- reset() ---

def test_reset_restores_hp_movement_and_resources(make_player):
    player = make_player()
    player.hp = 1
    player.movement = 0
    player.has_action = False
    player.has_bonus_action = False
    player.has_reaction = False

    player.reset()

    assert player.hp == player.max_hp
    assert player.movement == player.speed
    assert player.has_action is True
    assert player.has_bonus_action is True
    assert player.has_reaction is True

def test_reset_clears_all_effects(make_player):
    player = make_player()
    player.add_effect(Blind())
    assert player.has_effect(Blind)

    player.reset()

    assert not player.has_effect(Blind)

# --- heal() ---

def test_heal_increases_hp(make_player):
    player = make_player()
    player.hp = player.max_hp - 10
    player.heal(4)
    assert player.hp == player.max_hp - 6

def test_heal_does_not_exceed_max_hp(make_player):
    player = make_player()
    player.heal(999)
    assert player.hp == player.max_hp

# --- take_damage ---

def test_take_damage_reduces_hp_and_notifies_effects(make_player):
    player = make_player()
    notified = []

    class _WatchingEffect(Blind):
        def on_damage_taken(self, target, amount):
            notified.append(amount)

    player.add_effect(_WatchingEffect())
    starting_hp = player.hp

    player.take_damage(7, DamageType.BLUDGEONING)

    assert player.hp == starting_hp - 7
    assert notified == [7]

# --- take_damage: vulnerability / resistance / immunity ---

def test_resistance_halves_damage_of_the_matching_type(make_monster):
    monster = make_monster(damage_resistances = [DamageType.BLUDGEONING])
    starting_hp = monster.hp

    monster.take_damage(10, DamageType.BLUDGEONING)

    assert monster.hp == starting_hp - 5

def test_resistance_rounds_the_halved_damage_down(make_monster):
    monster = make_monster(damage_resistances = [DamageType.BLUDGEONING])
    starting_hp = monster.hp

    monster.take_damage(7, DamageType.BLUDGEONING) # 7 * 0.5 = 3.5, should round down to 3

    assert monster.hp == starting_hp - 3

def test_vulnerability_doubles_damage_of_the_matching_type(make_monster):
    monster = make_monster(damage_vulnerabilities = [DamageType.FIRE])
    starting_hp = monster.hp

    monster.take_damage(10, DamageType.FIRE)

    assert monster.hp == starting_hp - 20

def test_immunity_prevents_any_damage_of_the_matching_type(make_monster):
    monster = make_monster(damage_immunities = [DamageType.POISON])
    starting_hp = monster.hp

    monster.take_damage(999, DamageType.POISON)

    assert monster.hp == starting_hp

def test_immunity_takes_priority_over_resistance_and_vulnerability(make_monster):
    monster = make_monster(
        damage_immunities = [DamageType.FIRE],
        damage_vulnerabilities = [DamageType.FIRE]
    )
    starting_hp = monster.hp

    monster.take_damage(999, DamageType.FIRE)

    assert monster.hp == starting_hp

def test_resistance_to_one_damage_type_does_not_affect_another(make_monster):
    monster = make_monster(damage_resistances = [DamageType.FIRE])
    starting_hp = monster.hp

    monster.take_damage(10, DamageType.BLUDGEONING)

    assert monster.hp == starting_hp - 10

def test_effects_are_notified_with_the_mitigated_damage_amount(make_monster):
    monster = make_monster(damage_resistances = [DamageType.BLUDGEONING])
    notified = []

    class _WatchingEffect(Blind):
        def on_damage_taken(self, target, amount):
            notified.append(amount)

    monster.add_effect(_WatchingEffect())

    monster.take_damage(10, DamageType.BLUDGEONING)

    assert notified == [5] # effects should see the post-resistance amount, not the raw roll

def test_immune_target_does_not_notify_effects(make_monster):
    monster = make_monster(damage_immunities = [DamageType.POISON])
    notified = []

    class _WatchingEffect(Blind):
        def on_damage_taken(self, target, amount):
            notified.append(amount)

    monster.add_effect(_WatchingEffect())

    monster.take_damage(999, DamageType.POISON)

    assert notified == []

def test_take_damage_returns_the_actual_mitigated_amount(make_monster):
    normal = make_monster()
    resistant = make_monster(damage_resistances = [DamageType.FIRE])
    vulnerable = make_monster(damage_vulnerabilities = [DamageType.FIRE])
    immune = make_monster(damage_immunities = [DamageType.FIRE])

    assert normal.take_damage(10, DamageType.FIRE) == 10
    assert resistant.take_damage(10, DamageType.FIRE) == 5
    assert vulnerable.take_damage(10, DamageType.FIRE) == 20
    assert immune.take_damage(10, DamageType.FIRE) == 0