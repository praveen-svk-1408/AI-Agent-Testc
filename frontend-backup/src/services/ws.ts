import { WS_BASE_URL } from "@/lib/constants";
import type { WSEvent } from "@/types";

type WSCallback = (event: WSEvent) => void;

export function connectTestRunWS(
  runId: string,
  onMessage: WSCallback,
  onClose?: () => void
): WebSocket {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/test-runs/${runId}`);

  ws.onmessage = (event) => {
    try {
      const data: WSEvent = JSON.parse(event.data);
      onMessage(data);
    } catch {
      console.error("Failed to parse WebSocket message:", event.data);
    }
  };

  ws.onclose = () => {
    onClose?.();
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
  };

  return ws;
}
