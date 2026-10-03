import { useEffect, useRef, useState } from "react"
import { C, FONT, caps, labelStyle, headingStyle, panelStyle, selectStyle, inputStyle, hpColour } from "./theme"
import { getEncounters, getMonsters, simulateLive } from "./api"
import MonsterTags from "./MonsterTags"
import CombatGrid from "./CombatGrid"
import CombatLog from "./CombatLog"
import DecisionPanel from "./DecisionPanel"
import Button from "./Button"

function Roster({ positions, actingName }) {
  const side = team => positions.filter(p => p.team === team)
  const slotText = p => Object.entries(p.max_spell_slots).map(([level, max]) => `L${level} ${p.spell_slots[level] ?? 0}/${max}`).join("  ")

  return (
    <div style={{ ...panelStyle, boxSizing: "border-box", width: 480, flexShrink: 0, fontFamily: FONT, fontSize: 11 }}>
      <div style={{ ...headingStyle, marginBottom: 12 }}>Combatants</div>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        {[["party", "PCs", C.party], ["enemies", "Monsters", C.enemy]].map(([team, title, colour]) => (
          <div key={team} style={{ flex: "1 1 200px" }}>
            <div style={{ ...labelStyle, color: colour, marginBottom: 4 }}>{title}</div>
            {side(team).map(p => (
              <div key={p.name} style={{ marginBottom: 4, opacity: p.alive ? 1 : 0.4 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, color: p.name === actingName ? C.gold : C.text }}>
                  <span>{p.name}</span>
                  <span style={{ color: p.alive ? hpColour(p.hp, p.max_hp) : C.red }}>{p.alive ? `${p.hp}/${p.max_hp}` : "down"}</span>
                </div>
                {p.alive && (Object.keys(p.max_spell_slots).length > 0 || p.effects.length > 0) && (
                  <div style={{ color: C.textDim, fontSize: 10 }}>
                    {Object.keys(p.max_spell_slots).length > 0 && `Spell slots: ${slotText(p)}`}
                    {p.effects.map(e => <span key={e} style={{ color: C.purple, marginLeft: 6 }}>[{e}]</span>)}
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function LiveView() {
  const [encounters, setEncounters] = useState([])
  const [monsters, setMonsters] = useState([])
  const [encounter, setEncounter] = useState("")
  const [seedText, setSeedText] = useState("")
  const [frames, setFrames] = useState([])
  const [usedSeed, setUsedSeed] = useState(null)
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(800)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const timer = useRef(null)

  useEffect(() => {
    Promise.all([getEncounters(), getMonsters()])
      .then(([rows, monsterList]) => {
        setEncounters(rows)
        setMonsters(monsterList)
        if (rows.length) setEncounter(rows[0].id)
      })
      .catch(e => setError(`Could not reach the simulator: ${e.message}`))
  }, [])

  useEffect(() => {
    if (!playing || frames.length === 0) return undefined
    timer.current = setInterval(() => {
      setIndex(prev => {
        if (prev >= frames.length - 1) {
          setPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, speed)
    return () => clearInterval(timer.current)
  }, [playing, speed, frames])

  async function run() {
    setPlaying(false)
    setFrames([])
    setIndex(0)
    setError(null)
    setLoading(true)
    try {
      const seed = seedText.trim() === "" ? undefined : Number(seedText)
      if (seed !== undefined && !Number.isInteger(seed)) throw new Error("The seed must be a whole number (or left blank for a random fight).")
      const data = await simulateLive({ encounter, seed })
      setFrames(data.frames)
      setUsedSeed(data.seed)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const frame = frames[index]
  const last = frames.length - 1
  const decisions = frame?.decisions ?? []
  const actingName = decisions[0]?.combatant
  const actingTeam = frame?.positions.find(p => p.name === actingName)?.team
  const chosen = encounters.find(e => e.id === encounter)
  const step = to => { setPlaying(false); setIndex(to) }

  return (
    <div>
      <div style={{ ...panelStyle, marginBottom: 16 }}>
        <div style={{ ...headingStyle, marginBottom: 8 }}>Live combat</div>
        <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.6, marginBottom: 14 }}>
          <div>One fight, every decision explained.</div>
          <div>The grid is a fixed 10×10 of 5 ft squares. Each combatant starts in a random square on its side's back row.</div>
        </div>
        <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap", fontSize: 12 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            Encounter:
            <select value={encounter} onChange={e => setEncounter(e.target.value)} style={selectStyle}>
              {encounters.map(e => <option key={e.id} value={e.id}>{e.title}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            Seed:
            <input value={seedText} onChange={e => setSeedText(e.target.value)} placeholder="random" style={inputStyle} />
          </label>
          <Button onClick={run} disabled={loading || !encounter}>{loading ? "Computing..." : "Run combat"}</Button>
        </div>
        {chosen && (
          <div style={{ marginTop: 14 }}>
            {chosen.monsters.map(m => {
              const details = monsters.find(d => d.name === m.name)
              return (
                <div key={m.name} style={{ display: "flex", gap: 12, alignItems: "baseline", flexWrap: "wrap", fontSize: 12, lineHeight: 1.8 }}>
                  <span>{m.count} × {m.name}</span>
                  {details && <MonsterTags monster={details} />}
                </div>
              )
            })}
          </div>
        )}
        {usedSeed !== null && frames.length > 0 && (
          <div style={{ fontSize: 11, color: C.textDim, marginTop: 6 }}>
            Seed: <b style={{ color: C.text }}>{usedSeed}</b>
          </div>
        )}
        {error && <div style={{ fontSize: 12, color: C.red, marginTop: 10 }}>{error}</div>}
      </div>

      {frames.length > 0 && (
        <>
          <div style={{ ...panelStyle, position: "sticky", top: 0, zIndex: 5, display: "flex", gap: 8, alignItems: "center", marginBottom: 16, flexWrap: "wrap", padding: "10px 14px" }}>
            <Button onClick={() => step(0)} disabled={index === 0} variant="secondary">⏮</Button>
            <Button onClick={() => step(Math.max(0, index - 1))} disabled={index === 0} variant="secondary">◀</Button>
            <Button onClick={() => setPlaying(p => !p)} disabled={index === last}>{playing ? "⏸" : "▶"}</Button>
            <Button onClick={() => step(Math.min(last, index + 1))} disabled={index === last} variant="secondary">▶</Button>
            <Button onClick={() => step(last)} disabled={index === last} variant="secondary">⏭</Button>
            <span style={{ fontSize: 11, color: C.textDim, marginLeft: 4 }}>Step {index + 1} / {frames.length}</span>
            <label style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: 8, fontSize: 12 }}>
              Speed:
              <select value={speed} onChange={e => setSpeed(Number(e.target.value))} style={selectStyle}>
                <option value={1500}>Slow</option>
                <option value={800}>Normal</option>
                <option value={300}>Fast</option>
              </select>
            </label>
          </div>

          {frame.winner && (
            <div style={{ fontSize: 14, fontWeight: 700, color: frame.winner === "party" ? C.party : C.enemy, marginBottom: 16, ...caps }}>
              {frame.winner === "party" ? "⚔ Party victory" : frame.winner === "enemies" ? "💀 Party defeated" : "Draw"}
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", gap: 16, alignItems: "stretch", flexWrap: "wrap" }}>
              <div style={{ width: 480, flexShrink: 0 }}>
                <CombatGrid positions={frame.positions} actingName={actingName} />
              </div>
              <CombatLog frames={frames.slice(0, index + 1)} />
            </div>
            <div style={{ display: "flex", gap: 16, alignItems: "stretch", flexWrap: "wrap" }}>
              <Roster positions={frame.positions} actingName={actingName} />
              <DecisionPanel decisions={decisions} team={actingTeam} actingName={actingName} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
