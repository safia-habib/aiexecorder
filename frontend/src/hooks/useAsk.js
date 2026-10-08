import { useState, useCallback, useRef } from 'react'
import { streamAsk } from '../api/client'

export function useAsk() {
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const controllerRef = useRef(null)

  const ask = useCallback(async (stateCode, question) => {
    // Cancel any in-flight request before starting a new one
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    setLoading(true)
    setAnswer('')
    setError(null)

    try {
      for await (const event of streamAsk(stateCode, question, controller.signal)) {
        if (controller.signal.aborted) break
        if (event.type === 'token') {
          setAnswer(prev => prev + event.token)
        } else if (event.type === 'done') {
          setAnswer(event.fullAnswer)
          break
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    controllerRef.current?.abort()
    setAnswer('')
    setError(null)
    setLoading(false)
  }, [])

  return { answer, loading, error, ask, reset }
}
