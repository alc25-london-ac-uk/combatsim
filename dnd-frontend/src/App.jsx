import { useState } from "react"
import { C, T, FONT, TITLE_FONT, caps } from "./theme"
import MonteCarloView from "./MonteCarloView"
import LiveView from "./LiveView"

export default function App() {
  const [mode, setMode] = useState("monte")

  const tab = (id, label) => (
    <button
      onClick={() => setMode(id)}
      style={{
        backgroundColor: mode === id ? C.borderHi : "transparent",
        color: mode === id ? C.onFill : C.textDim,
        border: `${T.borderWidth}px solid ${mode === id ? C.borderHi : "transparent"}`,
        padding: "6px 16px",
        fontSize: 12,
        fontWeight: mode === id ? 700 : 400,
        fontFamily: FONT,
        cursor: "pointer",
        ...caps,
      }}
    >
      {label}
    </button>
  )

  return (
    <div style={{ minHeight: "100vh", backgroundColor: C.bg, color: C.text, padding: "32px 40px", fontFamily: FONT, boxSizing: "border-box", textAlign: "left" }}>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 22, fontWeight: 700, fontFamily: TITLE_FONT, ...caps }}>D&D Combat Simulator</div>
        <div style={{ fontSize: 11, color: C.textDim, marginTop: 4, lineHeight: 1.6 }}>
          <div>Party: Fighter, Cleric, Wizard (all level 5).</div>
          <div>Monsters use a greedy utility scorer.</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {tab("monte", "Monte Carlo")}
        {tab("live", "Live combat")}
      </div>

      {/* both views stay mounted so switching tabs does not lose results */}
      <div style={{ display: mode === "monte" ? "block" : "none" }}><MonteCarloView /></div>
      <div style={{ display: mode === "live" ? "block" : "none" }}><LiveView /></div>
    </div>
  )
}
