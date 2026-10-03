import { useEffect, useState } from "react"
import { C, FONT, BORDER, caps, headingStyle, panelStyle, selectStyle, inputStyle } from "./theme"
import { getMonsters, getEncounters, simulate } from "./api"
import Button from "./Button"
import MonsterTags from "./MonsterTags"

const MAX_MONSTERS = 12
const RUN_OPTIONS = [100, 200, 500]

const POLICY_LABELS = {
  Random:         { name: "Random",         note: "picks any legal action" },
  Greedy:         { name: "Greedy",         note: "fixed guesses, never updated" },
  BeliefUpdating: { name: "BeliefUpdating", note: "learns from what it observes" },
  Omniscient:     { name: "Omniscient",     note: "perfect information" },
}

let nextRowId = 1
const makeRow = (name, count = 1) => ({ id: nextRowId++, name, count })

function Results({ data }) {
  const maxSe = Math.max(...data.results.map(r => r.pc_win_se))
  return (
    <div style={{ ...panelStyle, marginTop: 16 }}>
      <div style={{ ...headingStyle, marginBottom: 8 }}>Results</div>
      <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.6, marginBottom: 14 }}>
        {data.runs.toLocaleString()} fights per policy, {data.monster_count} monsters
      </div>
      <table style={{ borderCollapse: "collapse", width: "100%", fontFamily: FONT, fontSize: 12 }}>
        <thead>
          <tr style={{ color: C.textDim, textAlign: "left", fontSize: 10, ...caps }}>
            <th style={{ fontWeight: 400, paddingBottom: 6 }}>PC policy</th>
            <th style={{ fontWeight: 400, width: "38%" }}>PC win rate</th>
            <th style={{ fontWeight: 400, textAlign: "right" }}>± SE</th>
            <th style={{ fontWeight: 400, textAlign: "right" }}>Monsters win</th>
            <th style={{ fontWeight: 400, textAlign: "right" }}>Draw</th>
            <th style={{ fontWeight: 400, textAlign: "right" }}>Avg rounds</th>
          </tr>
        </thead>
        <tbody>
          {data.results.map(r => {
            const label = POLICY_LABELS[r.policy]
            const low = Math.max(0, r.pc_win_pct - r.pc_win_se)
            const high = Math.min(100, r.pc_win_pct + r.pc_win_se)
            return (
              <tr key={r.policy} style={{ borderTop: BORDER }}>
                <td style={{ padding: "8px 8px 8px 0" }}>
                  <div style={{ color: C.text }}>{label?.name ?? r.policy}</div>
                  <div style={{ color: C.textDim, fontSize: 10 }}>{label?.note}</div>
                </td>
                <td style={{ paddingRight: 10 }}>
                  <div style={{ position: "relative", height: 14, backgroundColor: C.border }}>
                    <div style={{ width: `${r.pc_win_pct}%`, height: "100%", backgroundColor: C.party, transition: "width 0.6s ease" }} />
                    <div title={`${r.pc_win_pct.toFixed(1)}% ± ${r.pc_win_se.toFixed(1)}`}
                         style={{ position: "absolute", top: 5, height: 4, left: `${low}%`, width: `${Math.max(0.5, high - low)}%`, backgroundColor: C.gold, opacity: 0.9 }} />
                  </div>
                </td>
                <td style={{ textAlign: "right", color: C.party, fontWeight: 700 }}>
                  {r.pc_win_pct.toFixed(1)}% <span style={{ color: C.textDim, fontWeight: 400 }}>± {r.pc_win_se.toFixed(1)}</span>
                </td>
                <td style={{ textAlign: "right", color: C.enemy }}>{r.monster_win_pct.toFixed(1)}%</td>
                <td style={{ textAlign: "right", color: C.textDim }}>{r.draw_pct.toFixed(1)}%</td>
                <td style={{ textAlign: "right", color: C.text }}>{r.average_rounds.toFixed(1)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div style={{ fontSize: 10, color: C.textDim, marginTop: 12, lineHeight: 1.6 }}>
        The gold bar is one standard error either side of each win rate. At {data.runs.toLocaleString()} fights it is up to about ±{maxSe.toFixed(1)} points,
        so policies that differ by less than roughly {(2 * maxSe).toFixed(0)} points cannot be told apart here. The project's own evaluation uses
        10,000 fights per policy per encounter, where the standard error is about ±0.5.
        {data.seed !== null && `Seed ${data.seed}.`}
      </div>
    </div>
  )
}

export default function MonteCarloView() {
  const [monsters, setMonsters] = useState([])
  const [encounters, setEncounters] = useState([])
  const [rows, setRows] = useState([])
  const [runs, setRuns] = useState(100)
  const [seedText, setSeedText] = useState("")
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([getMonsters(), getEncounters()])
      .then(([monsterList, encounterList]) => {
        setMonsters(monsterList)
        setEncounters(encounterList)
        const first = encounterList[encounterList.length - 1]
        if (first) setRows(first.monsters.map(m => makeRow(m.name, m.count)))
      })
      .catch(e => setError(`Could not reach the simulator: ${e.message}`))
  }, [])

  const byName = Object.fromEntries(monsters.map(m => [m.name, m]))
  const total = rows.reduce((sum, r) => sum + r.count, 0)
  const tooMany = total > MAX_MONSTERS

  const update = (id, patch) => setRows(rs => rs.map(r => (r.id === id ? { ...r, ...patch } : r)))

  async function run() {
    setError(null)
    setLoading(true)
    setData(null)
    try {
      const seed = seedText.trim() === "" ? undefined : Number(seedText)
      if (seed !== undefined && !Number.isInteger(seed)) throw new Error("The seed must be a whole number (or left blank).")
      setData(await simulate({ monsters: rows.map(({ name, count }) => ({ name, count })), runs, seed }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ ...panelStyle, marginBottom: 16 }}>
        <div style={{ ...headingStyle, marginBottom: 8 }}>Build an encounter</div>
        <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.6, marginBottom: 14 }}>
          <div>Choose the monsters below, or start from one of the three preset encounters.</div>
          <div>The PCs will fight it using each of the four policies in turn: Random, Greedy, BeliefUpdating and Omniscient.</div>
          <div>Results appear underneath once all the fights have been run.</div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 14 }}>
          <span style={{ fontSize: 11, color: C.textDim }}>Preset encounters:</span>
          {encounters.map(e => (
            <Button key={e.id} variant="secondary" onClick={() => setRows(e.monsters.map(m => makeRow(m.name, m.count)))}>{e.title}</Button>
          ))}
        </div>

        {rows.map(row => {
          const monster = byName[row.name]
          return (
            <div key={row.id} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <select value={row.count} onChange={e => update(row.id, { count: Number(e.target.value) })} style={selectStyle} aria-label="quantity">
                  {Array.from({ length: MAX_MONSTERS }, (_, i) => i + 1).map(n => <option key={n} value={n}>{n} ×</option>)}
                </select>
                <select value={row.name} onChange={e => update(row.id, { name: e.target.value })} style={{ ...selectStyle, minWidth: 260 }} aria-label="monster">
                  {monsters.map(m => <option key={m.name} value={m.name}>{m.name} — CR {m.cr}, {m.hp} HP, AC {m.ac}</option>)}
                </select>
                <button onClick={() => setRows(rs => rs.filter(r => r.id !== row.id))} disabled={rows.length === 1} title="Remove"
                        style={{ ...selectStyle, color: rows.length === 1 ? C.textMuted : C.red, cursor: rows.length === 1 ? "not-allowed" : "pointer" }}>×</button>
                {monster && <MonsterTags monster={monster} />}
              </div>
            </div>
          )
        })}

        <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap", marginTop: 14, fontSize: 12 }}>
          <Button variant="secondary" disabled={monsters.length === 0}
                  onClick={() => setRows(rs => [...rs, makeRow(monsters[0].name)])}>+ Add monster</Button>
          <span style={{ color: tooMany ? C.red : C.textDim }}>{total} / {MAX_MONSTERS} monsters</span>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            Fights per policy:
            <select value={runs} onChange={e => setRuns(Number(e.target.value))} style={selectStyle}>
              {RUN_OPTIONS.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            Seed:
            <input value={seedText} onChange={e => setSeedText(e.target.value)} placeholder="random" style={inputStyle} />
          </label>
          <Button onClick={run} disabled={loading || tooMany || rows.length === 0}>
            {loading ? "Simulating..." : `Run ${(runs * 4).toLocaleString()} fights`}
          </Button>
        </div>
        {error && <div style={{ fontSize: 12, color: C.red, marginTop: 10 }}>{error}</div>}
      </div>

      {data && <Results data={data} />}
    </div>
  )
}
