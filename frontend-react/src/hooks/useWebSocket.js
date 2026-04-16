import { useEffect, useRef, useState, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * useWebSocket - Hook for WebSocket connections
 * 
 * @param path - WebSocket path (e.g., '/tasks/123')
 * @param options - Configuration options
 * @returns { connected, messages, send, reconnect }
 */
export function useWebSocket(path, options = {}) {
  const {
    onOpen,
    onMessage,
    onClose,
    onError,
    reconnectInterval = 3000,
    maxReconnects = 5,
    autoConnect = true
  } = options;

  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [reconnectCount, setReconnectCount] = useState(0);
  
  const ws = useRef(null);
  const reconnectTimer = useRef(null);
  const isManualClose = useRef(false);

  // Build WebSocket URL
  const getWsUrl = useCallback(() => {
    const baseUrl = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://');
    return `${baseUrl}/ws${path}`;
  }, [path]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const url = getWsUrl();
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setConnected(true);
        setReconnectCount(0);
        onOpen?.();
        
        // Send ping to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ action: 'ping' }));
          }
        }, 30000);
        
        ws.current.pingInterval = pingInterval;
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setMessages(prev => [...prev.slice(-50), data]); // Keep last 50 messages
          onMessage?.(data);
        } catch (err) {
          console.error('WebSocket message parse error:', err);
        }
      };

      ws.current.onclose = () => {
        setConnected(false);
        clearInterval(ws.current?.pingInterval);
        onClose?.();
        
        // Auto-reconnect if not manually closed
        if (!isManualClose.current && reconnectCount < maxReconnects) {
          reconnectTimer.current = setTimeout(() => {
            setReconnectCount(c => c + 1);
            connect();
          }, reconnectInterval);
        }
      };

      ws.current.onerror = (error) => {
        onError?.(error);
      };

    } catch (err) {
      console.error('WebSocket connection error:', err);
      onError?.(err);
    }
  }, [getWsUrl, onOpen, onMessage, onClose, onError, reconnectCount, maxReconnects, reconnectInterval]);

  // Disconnect
  const disconnect = useCallback(() => {
    isManualClose.current = true;
    clearTimeout(reconnectTimer.current);
    
    if (ws.current) {
      clearInterval(ws.current.pingInterval);
      ws.current.close();
      ws.current = null;
    }
    
    setConnected(false);
  }, []);

  // Send message
  const send = useCallback((data) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  // Manual reconnect
  const reconnect = useCallback(() => {
    isManualClose.current = false;
    setReconnectCount(0);
    disconnect();
    setTimeout(connect, 100);
  }, [disconnect, connect]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    connected,
    messages,
    send,
    connect,
    disconnect,
    reconnect,
    reconnectCount
  };
}

/**
 * useTaskWebSocket - Hook for real-time task updates
 * 
 * @param businessId - Business ID to subscribe to
 * @returns { tasks, updates, connected, subscribeTask }
 */
export function useTaskWebSocket(businessId) {
  const [tasks, setTasks] = useState([]);
  const [updates, setUpdates] = useState([]);
  
  const handleMessage = useCallback((data) => {
    switch (data.type) {
      case 'task_update':
        setUpdates(prev => [...prev, data]);
        
        // Update local tasks list
        if (data.data?.event === 'created') {
          setTasks(prev => [data.data.task, ...prev]);
        } else if (data.data?.event === 'status_changed') {
          setTasks(prev => prev.map(t => 
            t.id === data.data.task_id 
              ? { ...t, status: data.data.new_status }
              : t
          ));
        }
        break;
        
      case 'human_intervention_required':
        // Could trigger notification/toast
        console.log('Human intervention required:', data.task);
        break;
        
      default:
        break;
    }
  }, []);

  const { connected, send } = useWebSocket(
    `/tasks/${businessId}?token=${localStorage.getItem('token') || 'demo'}`,
    { onMessage: handleMessage }
  );

  const subscribeTask = useCallback((taskId) => {
    send({ action: 'subscribe_task', task_id: taskId });
  }, [send]);

  return {
    tasks,
    updates,
    connected,
    subscribeTask,
    send
  };
}
