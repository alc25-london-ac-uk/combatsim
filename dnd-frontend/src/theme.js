export const C = {
  bg:        "#383838",
  surface:   "#13161e",
  border:    "#1e2330",
  borderHi:  "#2e3550",
  party:     "#3b82f6",
  partyDim:  "#1e3a5f",
  enemy:     "#ef4444",
  enemyDim:  "#5f1e1e",
  dead:      "#2a2a2a",
  deadText:  "#444",
  gold:      "#f59e0b",
  text:      "#e2e8f0",
  textDim:   "#64748b",
  textMuted: "#334155",
  green:     "#22c55e",
  red:       "#ef4444",
  purple:    "#a78bfa",
  teal:      "#2dd4bf",
}

export const MONO = "'Courier New', monospace"

export const labelStyle = {
  fontSize: 10,
  color: C.textDim,
  textTransform: "uppercase",
  letterSpacing: "0.1em",
  fontFamily: MONO,
}

export const panelStyle = {
  backgroundColor: C.surface,
  border: `1px solid ${C.border}`,
  borderRadius: 4,
  padding: "14px 16px",
}

export const selectStyle = {
  backgroundColor: C.surface,
  border: `1px solid ${C.borderHi}`,
  borderRadius: 4,
  color: C.text,
  padding: "4px 8px",
  fontSize: 12,
  fontFamily: MONO,
  cursor: "pointer",
}

export const inputStyle = {
  ...selectStyle,
  cursor: "text",
  width: 90,
}

export function abbrev(name) {
  const parts = name.split(" ")
  if (parts.length === 1) return name.slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}

export function hpColour(hp, maxHp) {
  const pct = hp / maxHp
  if (pct > 0.6) return C.green
  if (pct > 0.25) return C.gold
  return C.red
}
