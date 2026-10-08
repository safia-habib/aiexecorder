import { useState, useEffect } from 'react'
import { fetchStateEO } from '../api/client'
import AskBox from './AskBox'

export default function StatePanel({ stateCode, stateMap, onClose }) {
  const [eoData, setEoData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!stateCode) {
      setEoData(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setEoData(null)
    setError(null)
    fetchStateEO(stateCode)
      .then(data => { if (!cancelled) setEoData(data) })
      .catch(err => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [stateCode])

  if (!stateCode) {
    return (
      <div style={s.placeholder}>
        <div style={s.placeholderHeading}>State AI EO Explorer</div>
        <p style={s.placeholderText}>
          Click any highlighted state on the map to view its AI executive order
          and the Dynatrace, Bindplane, and Arize capabilities that help agencies comply.
        </p>
        <p style={{ ...s.placeholderText, color: '#aaa', fontSize: '0.8rem', marginTop: '0.5rem' }}>
          Blue states have an AI executive order on file. Grey states do not.
        </p>
      </div>
    )
  }

  const stateName = stateMap[stateCode]?.state || stateCode

  return (
    <div style={s.panel}>
      <div style={s.header}>
        <div style={{ minWidth: 0 }}>
          <h2 style={s.stateName}>{stateName}</h2>
          {eoData?.has_eo && (
            <div style={s.meta}>
              <span style={s.badge}>{eoData.eo_name}</span>
              {eoData.date_issued && (
                <span style={s.metaText}>{eoData.date_issued}</span>
              )}
              {eoData.governor && (
                <span style={s.metaText}>Gov. {eoData.governor}</span>
              )}
            </div>
          )}
        </div>
        <button onClick={onClose} style={s.closeBtn} title="Deselect state" aria-label="Close panel">
          &#x2715;
        </button>
      </div>

      <div style={s.body}>
        {loading && <p style={s.hint}>Loading&hellip;</p>}
        {error && <p style={s.errorText}>{error}</p>}

        {eoData && !eoData.has_eo && (
          <div style={s.noEo}>
            <p style={s.noEoText}>No AI executive order on file for {stateName}.</p>
          </div>
        )}

        {eoData?.has_eo && (
          <>
            <Section title="Main Topics Covered" content={eoData.main_topics} />
            <Section
              title="Top Items for AI Workloads"
              content={eoData.top_items_for_ai_workloads}
            />
            <Section
              title="Dynatrace Features for Compliance"
              content={eoData.dynatrace_features}
              accent="#0073e6"
            />
            <Section
              title="Bindplane Features for Compliance"
              content={eoData.bindplane_features}
              accent="#6c3fa3"
            />
            <Section
              title="Arize Features for Compliance"
              content={eoData.arize_features}
              accent="#c45d00"
            />

            <div style={s.divider} />

            {/* key resets AskBox (and its in-flight requests) when state changes */}
            <AskBox key={stateCode} stateCode={stateCode} />
          </>
        )}
      </div>
    </div>
  )
}

function Section({ title, content, accent }) {
  if (!content) return null
  return (
    <div style={s.section}>
      <div style={{ ...s.sectionLabel, color: accent || '#444' }}>{title}</div>
      <p style={s.sectionContent}>{content}</p>
    </div>
  )
}

const s = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '0.5rem',
    padding: '1rem 1.25rem 0.8rem',
    borderBottom: '1px solid #e0e4e8',
    flexShrink: 0,
  },
  stateName: {
    fontSize: '1.15rem',
    fontWeight: 700,
    color: '#1a1a2e',
    marginBottom: '0.3rem',
  },
  meta: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: '0.5rem',
  },
  badge: {
    background: '#e8f3fc',
    color: '#1f618d',
    padding: '0.1rem 0.5rem',
    borderRadius: 4,
    fontSize: '0.78rem',
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
  metaText: {
    color: '#666',
    fontSize: '0.8rem',
  },
  closeBtn: {
    flexShrink: 0,
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#999',
    fontSize: '1rem',
    padding: '0.1rem 0.25rem',
    lineHeight: 1,
    borderRadius: 3,
  },
  body: {
    flex: 1,
    overflowY: 'auto',
    padding: '1rem 1.25rem 1.5rem',
  },
  hint: {
    color: '#888',
    fontSize: '0.85rem',
    margin: 0,
  },
  errorText: {
    color: '#c0392b',
    fontSize: '0.85rem',
    margin: 0,
  },
  noEo: {
    padding: '1.5rem 0',
    textAlign: 'center',
  },
  noEoText: {
    color: '#888',
    fontSize: '0.9rem',
    margin: 0,
    fontStyle: 'italic',
  },
  section: {
    marginBottom: '1rem',
  },
  sectionLabel: {
    fontSize: '0.72rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.6px',
    marginBottom: '0.3rem',
  },
  sectionContent: {
    margin: 0,
    fontSize: '0.875rem',
    lineHeight: 1.65,
    color: '#2c2c2c',
  },
  divider: {
    borderTop: '1px solid #e0e4e8',
    margin: '1.25rem 0',
  },
  placeholder: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    padding: '2.5rem 2rem',
    textAlign: 'center',
  },
  placeholderHeading: {
    fontSize: '0.9rem',
    fontWeight: 700,
    color: '#333',
    marginBottom: '0.75rem',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  placeholderText: {
    color: '#666',
    fontSize: '0.88rem',
    lineHeight: 1.65,
    margin: 0,
    maxWidth: 280,
  },
}
