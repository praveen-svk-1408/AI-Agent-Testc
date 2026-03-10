"use client";

import { useEffect, useRef, useState } from "react";
import { connectTestRunWS } from "@/services/ws";
import type { WSEvent } from "@/types";

export function useWebSocket(runId: string | null) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runId) return;

    const ws = connectTestRunWS(
      runId,
      (event) => {
        setEvents((prev) => [...prev, event]);
      },
      () => {
        setConnected(false);
      }
    );

    ws.onopen = () => setConnected(true);
    wsRef.current = ws;

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [runId]);

  const clearEvents = () => setEvents([]);

  return { events, connected, clearEvents };
}
