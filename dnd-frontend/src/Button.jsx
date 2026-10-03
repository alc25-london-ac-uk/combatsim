import { C, MONO } from "./theme"

export default function Button({ onClick, disabled, children, variant = "primary" }) {
  const bg = variant === "primary" ? C.party
    : variant === "danger"         ? C.enemy
    : C.borderHi
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        backgroundColor: disabled ? C.borderHi : bg,
        color: disabled ? C.textMuted : "white",
        border: "none",
        borderRadius: 4,
        padding: "8px 18px",
        fontSize: 12,
        fontWeight: 700,
        fontFamily: MONO,
        cursor: disabled ? "not-allowed" : "pointer",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        transition: "opacity 0.2s",
        opacity: disabled ? 0.5 : 1,
        minWidth: 36,
      }}
    >
      {children}
    </button>
  )
}
