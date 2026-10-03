import { C, FONT, BORDER, labelStyle, headingStyle, panelStyle } from "./theme"
import { PANEL_HEIGHT } from "./CombatGrid"
const TERMS = {
  expected_damage:       { colour: C.party,  label: "damage",    help: "Expected damage: chance to hit (or the target failing its save) × average damage, scaled by how resistant or vulnerable the target is believed to be. For an area spell this is summed over every enemy it catches." },
  friendly_fire:         { colour: C.red,    label: "friendly fire", help: "Expected damage to allies (or the caster) caught in the area of the spell. It is counted against the spell, so a cast that hits several enemies can still lose to one that hits fewer but spares your own side." },
  kill_bonus:            { colour: C.gold,   label: "kill",      help: "2 × the believed probability that this hit leaves the target at 0 HP." },
  priority_bonus:        { colour: C.purple, label: "priority",  help: "Extra value for opponents believed to be healers, concentrating on a spell, or still able to cast." },
  target_priority_bonus: { colour: C.teal,   label: "preferred", help: "The monsters' standing preference for weaker targets (the PCs have no such preference)." },
  healing_value:         { colour: C.green,  label: "healing",   help: "Expected healing × how badly the ally is hurt." },
  buff_value:            { colour: C.green,  label: "buff",      help: "Expected damage prevented over the next few rounds by the armour class this buff grants." },
  control_value:         { colour: C.teal,   label: "control",   help: "Value of disabling the target, scaled by how healthy it is believed to be." },
  movement_penalty:      { colour: C.red,    label: "distance",  help: "Cost of the distance still to close before the action can be made." },
  approach_penalty:      { colour: C.red,    label: "out of reach", help: "Out of reach this turn, so worth no damage; only a small preference for the option needing least movement." },
  concentration_penalty: { colour: C.red,    label: "concentration", help: "Casting another concentration spell would end the one already being held." },
  no_spell_slot:         { colour: C.red,    label: "no slot",   help: "No spell slot left at this level." },
  not_applicable:        { colour: C.red,    label: "n/a",       help: "This spell cannot be used on that target." },
}

const fmt = (value, digits = 1) => (value === null || value === undefined ? "?" : Number(value).toFixed(digits))
const termInfo = name => TERMS[name] ?? { colour: C.textDim, label: name, help: name }

function Chip({ children, colour = C.textDim, title }) {
  return (
    <span title={title} style={{
      display: "inline-block", fontSize: 10, color: colour, border: `1px solid ${colour}55`,
      padding: "0 4px", marginRight: 4, marginBottom: 2, whiteSpace: "nowrap",
    }}>{children}</span>
  )
}

function CandidateRow({ rank, candidate, scale }) {
  const positives = Object.entries(candidate.terms).filter(([, v]) => v > 0)
  const negatives = Object.entries(candidate.terms).filter(([, v]) => v < -0.005)
  return (
    <tr style={{ backgroundColor: candidate.chosen ? `${C.gold}18` : "transparent", verticalAlign: "top" }}>
      <td style={{ color: C.textDim, padding: "3px 6px 3px 0" }}>{candidate.chosen ? "▶" : rank}</td>
      <td style={{ padding: "3px 8px 3px 0", color: candidate.chosen ? C.gold : C.text, maxWidth: 190 }}>
        <span style={{ color: C.textDim }}>{candidate.kind === "spell" ? "✦" : "⚔"}</span> {candidate.label} → {candidate.target}
      </td>
      <td style={{ textAlign: "right", padding: "3px 8px 3px 0", color: C.text }}>{fmt(candidate.total)}</td>
      <td style={{ padding: "3px 0", minWidth: 130 }}>
        <div style={{ display: "flex", height: 8, width: "100%", backgroundColor: C.border, overflow: "hidden" }}>
          {positives.map(([name, value]) => (
            <div key={name} title={`${termInfo(name).label}: ${fmt(value)}`}
                 style={{ width: `${Math.min(100, (value / scale) * 100)}%`, backgroundColor: termInfo(name).colour }} />
          ))}
        </div>
        <div style={{ marginTop: 2 }}>
          {Object.entries(candidate.terms).filter(([, v]) => Math.abs(v) > 0.005).map(([name, value]) => (
            <Chip key={name} colour={termInfo(name).colour} title={termInfo(name).help}>
              {termInfo(name).label} {value > 0 ? "+" : ""}{fmt(value)}
            </Chip>
          ))}
          {negatives.length === 0 && positives.length === 0 && <Chip>nothing to score</Chip>}
        </div>
      </td>
    </tr>
  )
}

function DecisionBlock({ decision }) {
  const scale = Math.max(1, ...decision.candidates.map(c => Object.values(c.terms).filter(v => v > 0).reduce((a, b) => a + b, 0)))
  const chosen = decision.chosen
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 12, color: C.text, marginBottom: 6 }}>
        <span style={{ ...labelStyle, marginRight: 8 }}>{decision.bonus_action ? "Bonus action" : "Main action"}</span>
        {chosen
          ? <>chose <span style={{ color: C.gold }}>{chosen.label} → {chosen.target}</span></>
          : <span style={{ color: C.textDim }}>nothing worth doing</span>}
      </div>
      {decision.candidates.length > 0 && (
        <table style={{ borderCollapse: "collapse", fontSize: 11, fontFamily: FONT, width: "100%" }}>
          <thead>
            <tr style={{ color: C.textDim, textAlign: "left" }}>
              <th style={{ fontWeight: 400 }}>#</th><th style={{ fontWeight: 400 }}>option</th>
              <th style={{ fontWeight: 400, textAlign: "right", paddingRight: 8 }}>score</th><th style={{ fontWeight: 400 }}>made up of</th>
            </tr>
          </thead>
          <tbody>
            {decision.candidates.map((candidate, i) => (
              <CandidateRow key={`${candidate.label}-${candidate.target}-${i}`} rank={i + 1} candidate={candidate} scale={scale} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function mismatch(believed, actual, tolerance) {
  return believed !== null && believed !== undefined && Math.abs(believed - actual) >= tolerance
}

function BeliefRow({ enemy, showOrdinary }) {
  const hpOff = mismatch(enemy.hp.believed, enemy.hp.true, Math.max(3, enemy.hp.max * 0.15))
  const acOff = mismatch(enemy.ac.believed, enemy.ac.true, 1.5)
  const saves = enemy.saves.map(s => `${s.ability.slice(0, 3)} ${fmt(s.believed)} (true ${s.true})`).join("\n")
  // a fixed guess "knows" every damage type is ordinary, which is noise; a learner's tested-and-ordinary types are worth showing
  const damageTypes = enemy.damage_types.filter(d => showOrdinary || d.true !== 1 || (d.believed !== null && d.believed !== 1))
  const flagLabels = { healer: "healer", offensive_caster: "caster", concentrating: "concentrating", slots_depleted: "slots used up" }

  return (
    <tr style={{ verticalAlign: "top", borderTop: BORDER }}>
      <td style={{ padding: "4px 6px 4px 0", color: C.text, maxWidth: 90 }}>{enemy.name}</td>
      <td style={{ padding: "4px 6px 4px 0", whiteSpace: "nowrap", color: hpOff ? C.gold : C.text }}>
        {fmt(enemy.hp.believed, 0)} <span style={{ color: C.textDim }}>/</span> <span style={{ color: C.textDim }}>{enemy.hp.true}</span>
      </td>
      <td title={`Saving-throw modifiers, believed vs true:\n${saves}`} style={{ padding: "4px 6px 4px 0", whiteSpace: "nowrap", color: acOff ? C.gold : C.text }}>
        {fmt(enemy.ac.believed)} <span style={{ color: C.textDim }}>/</span> <span style={{ color: C.textDim }}>{enemy.ac.true}</span>
      </td>
      <td style={{ padding: "4px 8px 4px 0" }}>
        {damageTypes.length === 0 && <span style={{ color: C.textDim }}>{showOrdinary ? "nothing unusual" : "assumes no resistances"}</span>}
        {damageTypes.map(d => {
          const known = d.believed !== null
          const special = d.true !== 1
          const colour = !special ? C.textDim : known ? C.green : C.gold
          const text = known ? `${d.type} ×${fmt(d.believed)}` : `${d.type} ?`
          const title = known
            ? `Learned multiplier ×${fmt(d.believed)}; true ×${d.true}`
            : `Not discovered yet. True multiplier: ×${d.true}`
          return <Chip key={d.type} colour={colour} title={title}>{text}{special ? ` (×${d.true})` : ""}</Chip>
        })}
      </td>
      <td style={{ padding: "4px 0" }}>
        {Object.entries(enemy.flags).map(([key, flag]) => {
          if (flag.true === null) return null
          const wrong = Math.abs(flag.believed - (flag.true ? 1 : 0)) > 0.4
          if (!flag.true && flag.believed < 0.05) return null
          return (
            <Chip key={key} colour={wrong ? C.gold : C.textDim}
                  title={`${flagLabels[key]}: believed ${fmt(flag.believed * 100, 0)}%, truth: ${flag.true ? "yes" : "no"}`}>
              {flagLabels[key]} {fmt(flag.believed * 100, 0)}% ({flag.true ? "yes" : "no"})
            </Chip>
          )
        })}
      </td>
    </tr>
  )
}

export default function DecisionPanel({ decisions, team, actingName }) {
  const isPc = team === "party"
  const beliefs = decisions[0]?.beliefs ?? []

  return (
    <div style={{ ...panelStyle, flex: "1 1 520px", minWidth: 0, height: PANEL_HEIGHT, overflowY: "auto", boxSizing: "border-box", fontFamily: FONT }}>
      <div style={{ ...headingStyle, marginBottom: 8 }}>Decision panel</div>

      {decisions.length === 0 && (
        <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.6 }}>
          Step to a combatant's turn to see why it chose what it did: the best-scoring options, what each score is made of,
          and what the combatant believes about its enemies next to the truth.
        </div>
      )}

      {decisions.length > 0 && (
        <>
          <div style={{ fontSize: 13, color: isPc ? C.party : C.enemy, marginBottom: 10, fontWeight: 700 }}>
            {actingName} <span style={{ fontSize: 10, color: C.textDim, fontWeight: 400 }}>
              — {isPc ? "BeliefUpdating (learns from what it sees)" : "Greedy (fixed guesses, never updated)"}
            </span>
          </div>

          {decisions.map((decision, i) => <DecisionBlock key={i} decision={decision} />)}

          <div style={{ ...labelStyle, marginTop: 4, marginBottom: 6 }}>
            {isPc ? "What it believes about its enemies" : "What it assumes about its enemies"}
          </div>
          {beliefs.length === 0
            ? <div style={{ fontSize: 11, color: C.textDim }}>No living enemies.</div>
            : (
              <table style={{ borderCollapse: "collapse", fontSize: 11, fontFamily: FONT, width: "100%" }}>
                <thead>
                  <tr style={{ color: C.textDim, textAlign: "left" }}>
                    <th style={{ fontWeight: 400 }}>enemy</th><th style={{ fontWeight: 400 }}>HP</th><th style={{ fontWeight: 400 }}>AC</th>
                    <th style={{ fontWeight: 400 }}>damage types</th><th style={{ fontWeight: 400 }}>spellcasting</th>
                  </tr>
                </thead>
                <tbody>{beliefs.map(enemy => <BeliefRow key={enemy.name} enemy={enemy} showOrdinary={isPc} />)}</tbody>
              </table>
            )}
          <div style={{ fontSize: 10, color: C.textDim, marginTop: 8, lineHeight: 1.5 }}>
            HP and AC are shown as believed / true; in the other columns the true value is in brackets.
            Amber marks where the belief is wrong or undiscovered. Hover any chip for what it means.
            Damage-type multipliers: ×0.5 resistant, ×2 vulnerable, ×0 immune; "?" means that type has not been tried yet.
          </div>
        </>
      )}
    </div>
  )
}
