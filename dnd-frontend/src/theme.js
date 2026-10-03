export const C = {
  bg: "#f4f4ee", surface: "#ffffff", border: "#000000", borderHi: "#000000",
  party: "#2f5dff", partyDim: "#c2d1ff", enemy: "#ff4d4d", enemyDim: "#ffcaca",
  dead: "#d9d9d9", deadText: "#777777", gold: "#c98a00",
  text: "#000000", textDim: "#444444", textMuted: "#8a8a8a",
  green: "#00a651", red: "#e00000", purple: "#6b2fd6", teal: "#00847a", onFill: "#ffffff",
}

export const FONT = "'Courier New', monospace"
export const TITLE_FONT = "'Arial Black', Arial, Helvetica, sans-serif"

export const T = {
  borderWidth: 2,
  shadow: "4px 4px 0 #000000",
  letterSpacing: "0.06em",
}

export const BORDER = `${T.borderWidth}px solid ${C.border}`
export const BORDER_HI = `${T.borderWidth}px solid ${C.borderHi}`

document.documentElement.style.background = C.bg
document.documentElement.style.colorScheme = "light"

export const caps = { textTransform: "uppercase", letterSpacing: T.letterSpacing }

export const labelStyle = {
  fontSize: 10,
  color: C.textDim,
  ...caps,
  fontFamily: FONT,
}

export const headingStyle = {
  ...labelStyle,
  fontSize: 15,
  fontWeight: 700,
  color: C.text,
}

export const panelStyle = {
  backgroundColor: C.surface,
  border: BORDER,
  padding: "14px 16px",
  boxShadow: T.shadow,
}

export const selectStyle = {
  backgroundColor: C.surface,
  border: BORDER_HI,
  color: C.text,
  padding: "4px 8px",
  fontSize: 12,
  fontFamily: FONT,
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
