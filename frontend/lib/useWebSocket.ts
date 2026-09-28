"use client";

import { useState, useEffect, useRef, useCallback } from 'react';

export interface WebSocketEvent {
  event: string;
  timestamp: string;
  payload: Record<string, unknown>;
}


interface UseWebSocketOptions {
  url?: string;
  onEvent?: (event: WebSocketEvent) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket({
  url,
  onEvent,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10
}: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null);
  const [lastUpdateTimestamp, setLastUpdateTimestamp] = useState<Date | null>(null);
  const [recentEvents, setRecentEvents] = useState<WebSocketEvent[]>([]);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const resolveWebSocketUrl = useCallback(() => {
    if (url) return url;
    if (typeof window === 'undefined') return 'ws://localhost:8000/api/v1/ws/stream';
    const loc = window.location;
    const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    // If running frontend on 3000, backend is on 8000
    const host = loc.hostname;
    const port = loc.port === '3000' ? '8000' : (loc.port || '8000');
    return `${protocol}//${host}:${port}/api/v1/ws/stream`;
  }, [url]);

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return;

    try {
      const wsUrl = resolveWebSocketUrl();
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        setLastUpdateTimestamp(new Date());
      };

      ws.onmessage = (event) => {
        try {
          const parsed: WebSocketEvent = JSON.parse(event.data);
          setLastEvent(parsed);
          setLastUpdateTimestamp(new Date());
          setRecentEvents((prev) => [parsed, ...prev.slice(0, 49)]);

          if (onEvent) {
            onEvent(parsed);
          }
        } catch {
          // Ignore non-JSON messages (e.g. ping/pong)
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        socketRef.current = null;

        // Schedule auto-reconnect
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setIsConnected(false);
    }
  }, [resolveWebSocketUrl, onEvent, reconnectInterval, maxReconnectAttempts]);

  useEffect(() => {
    connect();

    // Ping interval to keep connection alive
    const pingTimer = setInterval(() => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send('ping');
      }
    }, 15000);

    return () => {
      clearInterval(pingTimer);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  const send = useCallback((message: string | object) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const payload = typeof message === 'string' ? message : JSON.stringify(message);
      socketRef.current.send(payload);
    }
  }, []);

  return {
    isConnected,
    lastEvent,
    lastUpdateTimestamp,
    recentEvents,
    send
  };
}
