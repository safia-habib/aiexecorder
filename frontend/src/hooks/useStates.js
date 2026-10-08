import { useState, useEffect } from 'react'
import { fetchStates } from '../api/client'

// Returns stateMap: { [state_code]: { state, state_code, has_eo, eo_name, governor, date_issued } }
export function useStates() {
  const [stateMap, setStateMap] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStates()
      .then(data => {
        const map = {}
        data.states.forEach(s => { map[s.state_code] = s })
        setStateMap(map)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return { stateMap, loading, error }
}
