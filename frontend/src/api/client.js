// All calls use a relative /api path so they work with:
//   - Vite dev server proxy (vite.config.js)
//   - nginx reverse proxy in Docker / k8s (nginx.conf)

export async function fetchStates() {
  const resp = await fetch('/api/states')
  if (!resp.ok) throw new Error(`Failed to fetch states: ${resp.status}`)
  return resp.json()
}

export async function fetchStateEO(stateCode) {
  const resp = await fetch(`/api/states/${stateCode}/eo`)
  if (!resp.ok) throw new Error(`Failed to fetch EO for ${stateCode}: ${resp.status}`)
  return resp.json()
}

// Async generator that yields { type: 'token', token } or { type: 'done', fullAnswer }.
export async function* streamAsk(stateCode, question, signal) {
  const resp = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state_code: stateCode, question }),
    signal,
  })
  if (!resp.ok) throw new Error(`Ask request failed: ${resp.status}`)

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data:')) continue
        const raw = line.slice(5).trim()
        if (!raw) continue
        try {
          const data = JSON.parse(raw)
          if (data.token !== undefined) {
            yield { type: 'token', token: data.token }
          } else if (data.full_answer !== undefined) {
            yield { type: 'done', fullAnswer: data.full_answer }
            return
          }
        } catch {
          // skip malformed lines
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
