import { useEffect, useRef } from "react"
import { C, FONT, caps, headingStyle, panelStyle } from "./theme"
import { PANEL_HEIGHT } from "./CombatGrid"

// the per-decision score lines ("-> attack score ...") are shown in the decision panel instead
const entries = lines => lines.filter(line => !line.trim().startsWith("->"))

function lineColour(line) {
  if (line.includes("is dead")) return C.red
  if (line.includes("heals")) return C.green
  if (line.includes("miss")) return C.textDim
  return C.text
}

function RoundHeading({ round }) {
  return (
    <div style={{ backgroundColor: C.text, color: C.onFill, fontWeight: 700, padding: "3px 8px", margin: "12px 0 6px", ...caps }}>
      Round {round}
    </div>
  )
}

function Turn({ frame }) {
  const team = frame.positions.find(p => p.name === frame.actor)?.team
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ color: team === "party" ? C.party : C.enemy, fontWeight: 700, borderBottom: `1px solid ${C.textMuted}`, paddingBottom: 2, marginBottom: 3 }}>
        {frame.actor}
      </div>
      {entries(frame.log).map((line, i) => (
        // pre-wrap keeps the indentation of the lines grouped under a multi-target spell
        <div key={i} style={{ color: lineColour(line), whiteSpace: "pre-wrap", paddingLeft: 10, marginBottom: 2 }}>{line}</div>
      ))}
    </div>
  )
}

export default function CombatLog({ frames }) {
  const boxRef = useRef(null)

  // keep the newest entry in view; scrolling the box itself (not scrollIntoView) leaves the page where it is
  useEffect(() => {
    const box = boxRef.current
    if (box) box.scrollTop = box.scrollHeight
  }, [frames.length])

  return (
    <div ref={boxRef} style={{
      flex: "1 1 340px",
      minWidth: 0,
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
      {frames.length === 0 && <div style={{ color: C.textDim }}>Awaiting combat...</div>}
      {frames.map((frame, i) => (
        frame.actor === null
          ? <RoundHeading key={i} round={frame.round} />
          : <Turn key={i} frame={frame} />
      ))}
    </div>
  )
}
