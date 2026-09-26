import { useState, useEffect, useRef } from "react"
 
const API = "http://127.0.0.1:8000"
 
const GRID_SIZE = 10
const CELL = 44
 
const C = {
  bg:        "#0d0f14",
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
}
 
function abbrev(name) {
  const parts = name.split(" ")
  if (parts.length === 1) return name.slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}
 
function hpColour(hp, maxHp) {
  const pct = hp / maxHp
  if (pct > 0.6) return C.green
  if (pct > 0.25) return C.gold
  return C.red
}
 
// ── CombatGrid ────────────────────────────────────────────────────────────────
function CombatGrid({ positions }) {
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
      const bg = !first
        ? C.surface
        : !first.alive
          ? C.dead
          : first.team === "party" ? C.partyDim : C.enemyDim
 
      cells.push(
        <div key={key} style={{
          width: CELL, height: CELL,
          border: `1px solid ${C.border}`,
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
                fontFamily: "'Courier New', monospace",
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
          <div style={{
            position: "absolute", bottom: 2, right: 3,
            fontSize: 8, color: C.textMuted,
            fontFamily: "'Courier New', monospace",
          }}>
            {x},{y}
          </div>
        </div>
      )
    }
  }
 
  return (
    <div>
      <div style={{
        fontSize: 10, color: C.textDim,
        textTransform: "uppercase", letterSpacing: "0.1em",
        marginBottom: 8,
        fontFamily: "'Courier New', monospace",
      }}>
        Combat Grid — {GRID_SIZE}×{GRID_SIZE}
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
      <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
        {[["party", C.party, "Party"], ["enemies", C.enemy, "Enemies"]].map(([, col, label]) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: col }} />
            <span style={{ fontSize: 11, color: C.textDim, fontFamily: "'Courier New', monospace" }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
 
// ── CombatLog ─────────────────────────────────────────────────────────────────
function CombatLog({ log }) {
  const bottomRef = useRef(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [log])
 
  return (
    <div style={{
      width: 360,
      height: CELL * GRID_SIZE + 32,
      overflowY: "auto",
      backgroundColor: C.surface,
      border: `1px solid ${C.border}`,
      borderRadius: 4,
      padding: "10px 12px",
      fontFamily: "'Courier New', monospace",
      fontSize: 11,
      color: C.text,
    }}>
      <div style={{
        fontSize: 10, color: C.textDim,
        textTransform: "uppercase", letterSpacing: "0.1em",
        marginBottom: 8,
      }}>
        Combat Log
      </div>
      {log.length === 0 && (
        <div style={{ color: C.textMuted }}>Awaiting combat...</div>
      )}
      {log.map((line, i) => {
        const isRound = line.startsWith("---")
        const isHit   = line.includes("hit")
        const isMiss  = line.includes("miss")
        const isHeal  = line.includes("heals")
        const isDead  = line.includes("-1 HP") || line.includes("dead")
        const colour  = isRound ? C.gold
          : isDead  ? C.red
          : isHeal  ? C.green
          : isHit   ? C.text
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
 
// ── MonteCarloResults ─────────────────────────────────────────────────────────
function MonteCarloResults({ results }) {
  if (!results) return null
  const { party_win_pct, enemy_win_pct, draw_pct, n } = results
  return (
    <div style={{
      backgroundColor: C.surface,
      border: `1px solid ${C.border}`,
      borderRadius: 4,
      padding: "16px 20px",
      marginTop: 16,
    }}>
      <div style={{
        fontSize: 10, color: C.textDim,
        textTransform: "uppercase", letterSpacing: "0.1em",
        marginBottom: 12,
        fontFamily: "'Courier New', monospace",
      }}>
        Results — {n.toLocaleString()} runs
      </div>
      {[
        ["Party wins",  party_win_pct, C.party],
        ["Enemies win", enemy_win_pct, C.enemy],
        ["Draws",       draw_pct,      C.textDim],
      ].map(([label, pct, col]) => (
        <div key={label} style={{ marginBottom: 10 }}>
          <div style={{
            display: "flex", justifyContent: "space-between",
            fontSize: 12, marginBottom: 4,
            fontFamily: "'Courier New', monospace",
          }}>
            <span style={{ color: C.textDim }}>{label}</span>
            <span style={{ color: col, fontWeight: 700 }}>{pct.toFixed(1)}%</span>
          </div>
          <div style={{ height: 6, backgroundColor: C.border, borderRadius: 3 }}>
            <div style={{
              width: `${pct}%`, height: "100%",
              backgroundColor: col, borderRadius: 3,
              transition: "width 0.8s ease",
            }} />
          </div>
        </div>
      ))}
    </div>
  )
}
 
// ── EncounterConfig ───────────────────────────────────────────────────────────
function EncounterConfig({ goblins, setGoblins, hobgoblins, setHobgoblins, runs, setRuns, showRuns }) {
  const sel = (val, set, options) => (
    <select
      value={val}
      onChange={e => set(Number(e.target.value))}
      style={{
        backgroundColor: C.surface,
        border: `1px solid ${C.borderHi}`,
        borderRadius: 4,
        color: C.text,
        padding: "4px 8px",
        fontSize: 12,
        fontFamily: "'Courier New', monospace",
        cursor: "pointer",
      }}
    >
      {options.map(n => <option key={n} value={n}>{n}</option>)}
    </select>
  )
 
  return (
    <div style={{
      backgroundColor: C.surface,
      border: `1px solid ${C.border}`,
      borderRadius: 4,
      padding: "14px 16px",
      marginBottom: 16,
    }}>
      <div style={{
        fontSize: 10, color: C.textDim,
        textTransform: "uppercase", letterSpacing: "0.1em",
        marginBottom: 12,
        fontFamily: "'Courier New', monospace",
      }}>
        Encounter Configuration
      </div>
      <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: C.text, fontFamily: "'Courier New', monospace" }}>
          Goblins {sel(goblins, setGoblins, [0,1,2,3,4,5,6,7,8])}
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: C.text, fontFamily: "'Courier New', monospace" }}>
          Hobgoblins {sel(hobgoblins, setHobgoblins, [0,1,2,3,4])}
        </label>
        {showRuns && (
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: C.text, fontFamily: "'Courier New', monospace" }}>
            Runs {sel(runs, setRuns, [100, 1000, 5000, 10000])}
          </label>
        )}
      </div>
    </div>
  )
}
 
// ── Button ────────────────────────────────────────────────────────────────────
function Button({ onClick, disabled, children, variant = "primary" }) {
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
        fontFamily: "'Courier New', monospace",
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
 
// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [mode, setMode] = useState("monte")
  const [goblins, setGoblins] = useState(4)
  const [hobgoblins, setHobgoblins] = useState(2)
  const [runs, setRuns] = useState(1000)
 
  // Monte Carlo
  const [mcResults, setMcResults] = useState(null)
  const [mcLoading, setMcLoading] = useState(false)
 
  // Live
  const [rounds, setRounds] = useState([])
  const [currentRound, setCurrentRound] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(800)
  const [liveLoading, setLiveLoading] = useState(false)
  const intervalRef = useRef(null)
 
  const currentState = rounds[currentRound]
  const positions    = currentState?.positions ?? []
  const liveWinner   = currentState?.winner ?? null
  const log          = rounds.slice(0, currentRound + 1).flatMap(r => r.log)
 
  // Auto-play effect
  useEffect(() => {
    if (playing && rounds.length > 0) {
      intervalRef.current = setInterval(() => {
        setCurrentRound(prev => {
          if (prev >= rounds.length - 1) {
            setPlaying(false)
            clearInterval(intervalRef.current)
            return prev
          }
          return prev + 1
        })
      }, speed)
    }
    return () => clearInterval(intervalRef.current)
  }, [playing, speed, rounds])
 
  async function runMonteCarlo() {
    setMcLoading(true)
    setMcResults(null)
    try {
      const res = await fetch(
        `${API}/simulate?goblins=${goblins}&hobgoblins=${hobgoblins}&n=${runs}`
      )
      setMcResults(await res.json())
    } finally {
      setMcLoading(false)
    }
  }
 
  async function runLive() {
    clearInterval(intervalRef.current)
    setPlaying(false)
    setRounds([])
    setCurrentRound(0)
    setLiveLoading(true)
    try {
      const res = await fetch(
        `${API}/simulate-live?goblins=${goblins}&hobgoblins=${hobgoblins}`
      )
      const data = await res.json()
      setRounds(data)
    } finally {
      setLiveLoading(false)
    }
  }
 
  const selStyle = {
    backgroundColor: C.surface,
    border: `1px solid ${C.borderHi}`,
    borderRadius: 4,
    color: C.text,
    padding: "4px 8px",
    fontSize: 12,
    fontFamily: "'Courier New', monospace",
    cursor: "pointer",
  }
 
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
        fontFamily: "'Courier New', monospace",
        cursor: "pointer",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
      }}
    >
      {label}
    </button>
  )
 
  return (
    <div style={{
      minHeight: "100vh",
      backgroundColor: C.bg,
      color: C.text,
      padding: "32px 40px",
      fontFamily: "'Courier New', monospace",
    }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: "0.05em" }}>
          D&D COMBAT SIMULATOR
        </div>
        <div style={{ fontSize: 11, color: C.textDim, marginTop: 4 }}>
          Party: Fighter + Cleric — Level 5
        </div>
      </div>
 
      {/* Tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {tab("monte", "Monte Carlo")}
        {tab("live",  "Live Combat")}
      </div>
 
      {/* Config */}
      <EncounterConfig
        goblins={goblins}       setGoblins={setGoblins}
        hobgoblins={hobgoblins} setHobgoblins={setHobgoblins}
        runs={runs}             setRuns={setRuns}
        showRuns={mode === "monte"}
      />
 
      {/* Monte Carlo mode */}
      {mode === "monte" && (
        <div>
          <Button onClick={runMonteCarlo} disabled={mcLoading}>
            {mcLoading ? "Simulating..." : `Run ${runs.toLocaleString()} Simulations`}
          </Button>
          <MonteCarloResults results={mcResults} />
        </div>
      )}
 
      {/* Live mode */}
      {mode === "live" && (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Button onClick={runLive} disabled={liveLoading}>
              {liveLoading ? "Computing..." : "Run Combat"}
            </Button>
          </div>
 
          {/* Playback controls */}
          {rounds.length > 0 && (
            <div style={{
              display: "flex", gap: 8, alignItems: "center",
              marginBottom: 16,
              backgroundColor: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 4,
              padding: "10px 14px",
              flexWrap: "wrap",
            }}>
              <Button
                onClick={() => { setPlaying(false); setCurrentRound(0) }}
                disabled={currentRound === 0}
                variant="secondary"
              >⏮</Button>
 
              <Button
                onClick={() => { setPlaying(false); setCurrentRound(r => Math.max(0, r - 1)) }}
                disabled={currentRound === 0}
                variant="secondary"
              >◀</Button>
 
              <Button
                onClick={() => setPlaying(p => !p)}
                disabled={currentRound === rounds.length - 1}
              >
                {playing ? "⏸" : "▶"}
              </Button>
 
              <Button
                onClick={() => { setPlaying(false); setCurrentRound(r => Math.min(rounds.length - 1, r + 1)) }}
                disabled={currentRound === rounds.length - 1}
                variant="secondary"
              >▶</Button>
 
              <Button
                onClick={() => { setPlaying(false); setCurrentRound(rounds.length - 1) }}
                disabled={currentRound === rounds.length - 1}
                variant="secondary"
              >⏭</Button>
 
              <span style={{ fontSize: 11, color: C.textDim, marginLeft: 4 }}>
                Action {currentRound + 1} / {rounds.length}
              </span>
 
              <select
                value={speed}
                onChange={e => setSpeed(Number(e.target.value))}
                style={{ ...selStyle, marginLeft: 8 }}
              >
                <option value={1500}>Slow</option>
                <option value={800}>Normal</option>
                <option value={300}>Fast</option>
                <option value={100}>Very Fast</option>
              </select>
            </div>
          )}
 
          {/* Winner banner */}
          {liveWinner && (
            <div style={{
              fontSize: 14, fontWeight: 700,
              color: liveWinner === "party" ? C.party : C.enemy,
              marginBottom: 16,
              textTransform: "uppercase",
              letterSpacing: "0.1em",
            }}>
              {liveWinner === "party" ? "⚔ Party Victory" : "💀 Party Defeated"}
            </div>
          )}
 
          {/* Grid + Log */}
          {rounds.length > 0 && (
            <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
              <CombatGrid positions={positions} />
              <CombatLog log={log} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}