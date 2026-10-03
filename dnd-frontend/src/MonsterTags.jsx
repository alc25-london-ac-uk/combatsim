import { C } from "./theme"

export default function MonsterTags({ monster }) {
  const groups = [
    ["vulnerabilities", monster.vulnerabilities, C.green],
    ["resistances", monster.resistances, C.gold],
    ["immunities", monster.immunities, C.red],
  ]
  return (
    <span style={{ fontSize: 10 }}>
      {groups.filter(([, list]) => list.length > 0).map(([label, list, colour]) => (
        <span key={label} style={{ color: colour, marginRight: 10 }}>{label}: {list.join(", ")}</span>
      ))}
      {monster.spells.length > 0 && <span style={{ color: C.purple }}>spells: {monster.spells.join(", ")}</span>}
    </span>
  )
}
