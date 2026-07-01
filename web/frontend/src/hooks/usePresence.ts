import { useEffect, useState } from "react";
import { createPresenceWebSocket, getPresence } from "../api";
import type { PresenceStats } from "../types";

const EMPTY: PresenceStats = { online_sessions: 0, online_connections: 0 };

export function usePresence(): PresenceStats {
  const [stats, setStats] = useState<PresenceStats>(EMPTY);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let stopped = false;

    const fallbackPoll = () => {
      pollTimer = setInterval(async () => {
        try {
          const data = await getPresence();
          if (!stopped) setStats(data);
        } catch {
          // ignore transient errors
        }
      }, 5000);
    };

    try {
      ws = createPresenceWebSocket((data) => {
        if (!stopped) setStats(data);
      });
      ws.onclose = () => {
        if (!stopped && !pollTimer) fallbackPoll();
      };
      ws.onerror = () => {
        if (!stopped && !pollTimer) fallbackPoll();
      };
    } catch {
      fallbackPoll();
    }

    // Initial snapshot via REST so the UI isn't blank until first WS push.
    void getPresence()
      .then((data) => {
        if (!stopped) setStats(data);
      })
      .catch(() => {
        // ignore
      });

    return () => {
      stopped = true;
      if (pollTimer) clearInterval(pollTimer);
      if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        try {
          ws.close();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  return stats;
}
