import { useRef, useEffect, useCallback, useState } from 'react'
import type { WsMessage, WsTestStep } from '../types'

export function useTestRunSocket(runId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const [steps, setSteps] = useState<WsTestStep[]>([])
  const [status, setStatus] = useState<string | null>(null)
  const [connected, setConnected] = useState(false)

  const connect = useCallback(() => {
    if (!runId) return
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/test-runs/${runId}`)

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)

    ws.onmessage = (e) => {
      const msg: WsMessage = JSON.parse(e.data)
      switch (msg.event) {
        case 'status_change':
          setStatus(msg.status)
          break
        case 'test_step':
          setSteps(prev => [...prev, msg])
          break
        case 'artifact_ready':
          break
      }
    }

    wsRef.current = ws
  }, [runId])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  const reset = useCallback(() => {
    setSteps([])
    setStatus(null)
  }, [])

  useEffect(() => {
    connect()
    return disconnect
  }, [connect, disconnect])

  return { steps, status, connected, reset, disconnect }
}
