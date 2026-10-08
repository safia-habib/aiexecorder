import { useState } from 'react'
import { useAsk } from '../hooks/useAsk'

export default function AskBox({ stateCode }) {
  const [question, setQuestion] = useState('')
  const { answer, loading, error, ask, reset } = useAsk()

  function handleSubmit(e) {
    e.preventDefault()
    const q = question.trim()
    if (!q || loading) return
    setQuestion('')
    ask(stateCode, q)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e)
    }
  }

  return (
    <div>
      <div style={s.label}>Ask a follow-up question</div>
      <form onSubmit={handleSubmit} style={s.form}>
        <textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. How does Dynatrace help with model transparency requirements?"
          rows={2}
          disabled={loading}
          style={s.textarea}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          style={{ ...s.btn, ...(loading || !question.trim() ? s.btnDisabled : {}) }}
        >
          {loading ? '...' : 'Ask'}
        </button>
      </form>

      {(answer || loading) && (
        <div style={s.answer}>
          {answer ? (
            <>
              {answer}
              {loading && <span style={s.cursor}>|</span>}
            </>
          ) : (
            <span style={s.generating}>Generating answer...</span>
          )}
        </div>
      )}

      {error && <p style={s.error}>{error}</p>}

      {answer && !loading && (
        <button onClick={reset} style={s.clearBtn}>Clear</button>
      )}
    </div>
  )
}

const s = {
  label: {
    fontSize: '0.75rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.6px',
    color: '#555',
    marginBottom: '0.5rem',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem',
  },
  textarea: {
    width: '100%',
    padding: '0.5rem 0.7rem',
    fontSize: '0.85rem',
    border: '1px solid #ccd0d5',
    borderRadius: 6,
    resize: 'vertical',
    fontFamily: 'inherit',
    lineHeight: 1.5,
    outline: 'none',
    color: '#1a1a2e',
  },
  btn: {
    alignSelf: 'flex-end',
    padding: '0.4rem 1.1rem',
    background: '#0073e6',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontSize: '0.85rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  btnDisabled: {
    background: '#a0c4e8',
    cursor: 'not-allowed',
  },
  answer: {
    marginTop: '0.75rem',
    padding: '0.75rem',
    background: '#f4f6f9',
    border: '1px solid #e4e8ed',
    borderRadius: 6,
    fontSize: '0.875rem',
    lineHeight: 1.7,
    color: '#1a1a2e',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  generating: {
    color: '#888',
    fontStyle: 'italic',
  },
  cursor: {
    animation: 'blink 1s step-end infinite',
    color: '#0073e6',
    fontWeight: 'bold',
    marginLeft: 1,
  },
  error: {
    margin: '0.5rem 0 0',
    color: '#c0392b',
    fontSize: '0.82rem',
  },
  clearBtn: {
    marginTop: '0.4rem',
    background: 'none',
    border: 'none',
    color: '#999',
    fontSize: '0.78rem',
    cursor: 'pointer',
    padding: 0,
    textDecoration: 'underline',
  },
}
