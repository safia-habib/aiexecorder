import { useState } from 'react'
import { useStates } from './hooks/useStates'
import StateMap from './components/StateMap'
import StatePanel from './components/StatePanel'

export default function App() {
  const { stateMap, loading, error } = useStates()
  const [selectedCode, setSelectedCode] = useState(null)

  return (
    <div style={s.root}>
      <header style={s.header}>
        <h1 style={s.title}>State AI EO Explorer</h1>
        <span style={s.subtitle}>
          Governor AI executive orders &middot; Dynatrace / Bindplane / Arize compliance capabilities
        </span>
      </header>

      <div style={s.main}>
        {/* ── Map pane ──────────────────────────────────────────────── */}
        <div style={s.mapPane}>
          {loading && (
            <div style={s.centered}>
              <p style={s.statusText}>Loading state data&hellip;</p>
            </div>
          )}
          {error && (
            <div style={s.centered}>
              <p style={{ ...s.statusText, color: '#c0392b' }}>
                Could not load state data: {error}
              </p>
              <p style={{ ...s.statusText, fontSize: '0.8rem', color: '#888' }}>
                Make sure the backend is running and reachable at /api/states.
              </p>
            </div>
          )}
          {!loading && !error && (
            <>
              <StateMap
                stateMap={stateMap}
                selectedCode={selectedCode}
                onSelect={setSelectedCode}
              />
              <Legend />
            </>
          )}
        </div>

        {/* ── Detail panel ──────────────────────────────────────────── */}
        <div style={s.detailPane}>
          <StatePanel
            stateCode={selectedCode}
            stateMap={stateMap}
            onClose={() => setSelectedCode(null)}
          />
        </div>
      </div>
    </div>
  )
}

function Legend() {
  return (
    <div style={s.legend}>
      <LegendItem color="#2980b9" label="Has AI executive order — click to explore" />
      <LegendItem color="#d5d8dc" bordered label="No AI executive order on file" />
    </div>
  )
}

function LegendItem({ color, bordered, label }) {
  return (
    <div style={s.legendItem}>
      <div
        style={{
          width: 13,
          height: 13,
          background: color,
          border: bordered ? '1px solid #aaa' : 'none',
          borderRadius: 2,
          flexShrink: 0,
        }}
      />
      <span style={s.legendLabel}>{label}</span>
    </div>
  )
}

const s = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    overflow: 'hidden',
  },
  header: {
    background: '#1a1a2e',
    color: '#ffffff',
    padding: '0.7rem 1.5rem',
    display: 'flex',
    alignItems: 'baseline',
    gap: '1rem',
    flexShrink: 0,
  },
  title: {
    fontSize: '1rem',
    fontWeight: 700,
    letterSpacing: '0.2px',
    whiteSpace: 'nowrap',
  },
  subtitle: {
    color: '#8899bb',
    fontSize: '0.8rem',
  },
  main: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  mapPane: {
    flex: '0 0 62%',
    padding: '0.75rem 0.75rem 0.5rem',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  detailPane: {
    flex: '0 0 38%',
    background: '#ffffff',
    borderLeft: '1px solid #dde1e7',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  centered: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    textAlign: 'center',
  },
  statusText: {
    color: '#666',
    fontSize: '0.9rem',
    margin: '0 0 0.5rem',
  },
  legend: {
    display: 'flex',
    gap: '1.5rem',
    padding: '0.5rem 0.25rem',
    flexShrink: 0,
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
  },
  legendLabel: {
    fontSize: '0.78rem',
    color: '#555',
  },
}
