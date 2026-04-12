import { useState, useEffect, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export function useLedger() {
  const [status, setStatus] = useState(null);
  const [constitution, setConstitution] = useState(null);
  const [memory, setMemory] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);

  // Fetch initial status
  useEffect(() => {
    fetch(`${API_BASE}/ledger/status`)
      .then(r => r.json())
      .then(setStatus);
    
    fetch(`${API_BASE}/ledger/constitution`)
      .then(r => r.json())
      .then(setConstitution);
    
    fetch(`${API_BASE}/ledger/memory`)
      .then(r => r.json())
      .then(setMemory);
    
    fetch(`${API_BASE}/ledger/decisions`)
      .then(r => r.json())
      .then(setDecisions);
  }, []);

  // WebSocket connection
  useEffect(() => {
    const websocket = new WebSocket(`ws://${API_BASE.replace('http://', '')}/ledger/ws`);
    
    websocket.onopen = () => setConnected(true);
    websocket.onclose = () => setConnected(false);
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'command_result') {
        // Handle command result
      }
    };
    
    setWs(websocket);
    
    return () => websocket.close();
  }, []);

  const sendCommand = useCallback(async (command, context = {}) => {
    // REST API fallback
    const response = await fetch(`${API_BASE}/ledger/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command, context })
    });
    return response.json();
  }, []);

  const checkConstitution = useCallback(async (action) => {
    const response = await fetch(`${API_BASE}/ledger/check-constitution`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action)
    });
    return response.json();
  }, []);

  return {
    status,
    constitution,
    memory,
    decisions,
    connected,
    sendCommand,
    checkConstitution
  };
}
