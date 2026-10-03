import { useState } from "react"
import { C, MONO } from "./theme"
import MonteCarloView from "./MonteCarloView"
import LiveView from "./LiveView"

export default function App() {
  const [mode, setMode] = useState("monte")

  const tab = (id, label) => (
    <button
      onClick={() => setMode(id)}
      style={{
        backgroundColor: mode === id ? C.borderHi : "transparent",
        color: mode === id ? C.text : C.textDim,
        border: `1px solid ${mode === id ? C.borderHi : "transparent"}`,
        borderRadius: 4,
        padding: "6px 16px",
        fontSize: 12,
        fontWeight: mode === id ? 700 : 400,
        fontFamily: MONO,
        cursor: "pointer",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
      }}
    >
      {label}
    </button>
  )

  return (
    <div style={{ minHeight: "100vh", backgroundColor: C.bg, color: C.text, padding: "32px 40px", fontFamily: MONO, boxSizing: "border-box", textAlign: "left" }}>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: "0.05em" }}>D&D COMBAT SIMULATOR</div>
        <div style={{ fontSize: 11, color: C.textDim, marginTop: 4 }}>
          Party: level-5 Fighter, Cleric and Wizard. The monsters always play the Greedy baseline; the PCs' policy is what changes.
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
