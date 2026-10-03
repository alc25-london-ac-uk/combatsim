const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000"

async function request(path, options) {
  const response = await fetch(`${API}${path}`, options)
  if (!response.ok) {
    let detail = null
    try {
      detail = (await response.json()).detail
    } catch {
      // not JSON: fall through to the generic message
    }
    if (typeof detail === "string") throw new Error(detail)
    if (Array.isArray(detail)) throw new Error(detail.map(d => d.msg).join("; "))
    throw new Error(`Request failed (${response.status})`)
  }
  return response.json()
}

const post = (path, body) => request(path, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
})

export const getMonsters = () => request("/monsters")
export const getEncounters = () => request("/encounters")
export const simulate = body => post("/simulate", body)
export const simulateLive = body => post("/simulate-live", body)
