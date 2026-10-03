import { useEffect, useRef } from "react"
import { C, MONO, labelStyle } from "./theme"
import { CELL, GRID_SIZE } from "./CombatGrid"

export default function CombatLog({ log }) {
  const bottomRef = useRef(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
  }, [log])

  // the per-decision score lines ("-> attack score ...") are shown in the decision panel instead
  const lines = log.filter(line => !line.trim().startsWith("->"))

  return (
    <div style={{
      width: 340,
      height: CELL * GRID_SIZE + 32,
      overflowY: "auto",
      backgroundColor: C.surface,
      border: `1px solid ${C.border}`,
      borderRadius: 4,
      padding: "10px 12px",
      fontFamily: MONO,
      fontSize: 11,
      color: C.text,
      boxSizing: "border-box",
    }}>
      <div style={{ ...labelStyle, marginBottom: 8 }}>Combat Log</div>
      {lines.length === 0 && <div style={{ color: C.textMuted }}>Awaiting combat...</div>}
      {lines.map((line, i) => {
        const isRound = line.startsWith("---")
        const isMiss  = line.includes("miss")
        const isHeal  = line.includes("heals")
        const isDead  = line.includes("-1 HP") || line.includes("dead")
        const colour  = isRound ? C.gold
          : isDead  ? C.red
          : isHeal  ? C.green
          : isMiss  ? C.textDim
          : C.text
        return (
          <div key={i} style={{
            color: colour,
            marginBottom: isRound ? 6 : 2,
            borderTop: isRound ? `1px solid ${C.border}` : "none",
            paddingTop: isRound ? 6 : 0,
            fontWeight: isRound ? 700 : 400,
          }}>
            {line}
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
