import { useEffect, useRef } from "react"
import { C, FONT, BORDER, headingStyle, panelStyle } from "./theme"
import { PANEL_HEIGHT } from "./CombatGrid"

export default function CombatLog({ log }) {
  const bottomRef = useRef(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
  }, [log])

  const lines = log.filter(line => !line.trim().startsWith("->"))

  return (
    <div style={{
      width: 340,
      height: PANEL_HEIGHT,
      overflowY: "auto",
      ...panelStyle,
      padding: "10px 12px",
      fontFamily: FONT,
      fontSize: 11,
      color: C.text,
      boxSizing: "border-box",
    }}>
      <div style={{ ...headingStyle, marginBottom: 8 }}>Combat log</div>
      {lines.length === 0 && <div style={{ color: C.textDim }}>Awaiting combat...</div>}
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
            borderTop: isRound ? BORDER : "none",
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
