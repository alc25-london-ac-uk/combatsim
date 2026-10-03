import { C, T, FONT, BORDER, caps } from "./theme"

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
        color: disabled ? C.textMuted : C.onFill,
        border: BORDER,
        boxShadow: disabled ? "none" : T.shadow,
        padding: "8px 18px",
        fontSize: 12,
        fontWeight: 700,
        fontFamily: FONT,
        cursor: disabled ? "not-allowed" : "pointer",
        ...caps,
        transition: "opacity 0.2s",
        opacity: disabled ? 0.5 : 1,
        minWidth: 36,
      }}
    >
      {children}
    </button>
  )
}
