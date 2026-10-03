import { C, MONO, labelStyle, abbrev, hpColour } from "./theme"

const GRID_SIZE = 10
const CELL = 44

export { GRID_SIZE, CELL }

export default function CombatGrid({ positions, actingName }) {
  const occupants = {}
  for (const c of positions) {
    const key = `${c.x},${c.y}`
    if (!occupants[key]) occupants[key] = []
    occupants[key].push(c)
  }

  const cells = []
  for (let y = GRID_SIZE - 1; y >= 0; y--) {
    for (let x = 0; x < GRID_SIZE; x++) {
      const key = `${x},${y}`
      const here = occupants[key] || []
      const first = here[0]
      const acting = here.some(c => c.name === actingName)
      const bg = !first
        ? C.surface
        : !first.alive
          ? C.dead
          : first.team === "party" ? C.partyDim : C.enemyDim

      cells.push(
        <div key={key} title={here.map(c => `${c.name}: ${c.hp}/${c.max_hp} HP`).join("\n")} style={{
          width: CELL, height: CELL,
          boxSizing: "border-box",
          border: acting ? `2px solid ${C.gold}` : `1px solid ${C.border}`,
          backgroundColor: bg,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 1,
          position: "relative",
          transition: "background-color 0.3s ease",
        }}>
          {here.map((c, i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div style={{
                fontSize: 11,
                fontWeight: 700,
                fontFamily: MONO,
                color: !c.alive ? C.deadText : c.team === "party" ? C.party : C.enemy,
                lineHeight: 1,
              }}>
                {abbrev(c.name)}
              </div>
              {c.alive && (
                <div style={{
                  width: 28, height: 3,
                  backgroundColor: C.border,
                  borderRadius: 2, marginTop: 2,
                  overflow: "hidden",
                }}>
                  <div style={{
                    width: `${Math.max(0, (c.hp / c.max_hp) * 100)}%`,
                    height: "100%",
                    backgroundColor: hpColour(c.hp, c.max_hp),
                    transition: "width 0.4s ease",
                  }} />
                </div>
              )}
            </div>
          ))}
        </div>
      )
    }
  }

  return (
    <div>
      <div style={{ ...labelStyle, marginBottom: 8 }}>
        Combat Grid — {GRID_SIZE}×{GRID_SIZE} (each square 5 ft)
      </div>
      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${GRID_SIZE}, ${CELL}px)`,
        border: `2px solid ${C.borderHi}`,
        borderRadius: 4,
        overflow: "hidden",
      }}>
        {cells}
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: 8, flexWrap: "wrap" }}>
        {[[C.party, "PCs (BeliefUpdating)"], [C.enemy, "Monsters (Greedy)"], [C.gold, "Acting now"]].map(([col, label]) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: col }} />
            <span style={{ fontSize: 11, color: C.textDim, fontFamily: MONO }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
