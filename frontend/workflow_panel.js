/**
 * Room Workflow Panel - Ticket 8 UI Implementation
 * Integrates workflow launching and monitoring into AgentVerse 3D UI
 */

class RoomWorkflowPanel {
    constructor(world3D) {
        this.world = world3D;
        this.currentRoomId = null;
        this.activeRunId = null;
        this.pollingInterval = null;
        this.virtualAgents = new Map();
        
        // API endpoints
        this.apiBase = '/api';  // Will be configured based on deployment
        this.adapterUrl = 'http://localhost:8002';
        
        this.init();
    }
    
    init() {
        this.createPanelHTML();
        this.attachEventListeners();
        this.injectStyles();
        console.log('🎛️ RoomWorkflowPanel initialized');
    }
    
    createPanelHTML() {
        // Create workflow panel container
        const panel = document.createElement('div');
        panel.id = 'workflow-panel';
        panel.className = 'workflow-panel';
        panel.innerHTML = `
            <div class="workflow-header">
                <h3>🚀 Workflow Launcher</h3>
                <span class="engine-badge" id="engine-badge">MOCK</span>
            </div>
            
            <!-- Binding Status -->
            <div class="binding-status" id="binding-status">
                <p class="status-text">Checking room binding...</p>
            </div>
            
            <!-- Launch Section -->
            <div class="launch-section" id="launch-section" style="display: none;">
                <div class="input-group">
                    <label>Subreddit</label>
                    <select id="subreddit-input">
                        <option value="sidehustle">r/sidehustle</option>
                        <option value="entrepreneur">r/entrepreneur</option>
                        <option value="passive_income">r/passive_income</option>
                        <option value="startups">r/startups</option>
                        <option value="marketing">r/marketing</option>
                    </select>
                </div>
                
                <div class="input-group">
                    <label>Min Upvotes</label>
                    <input type="number" id="upvotes-input" value="100" min="10" max="10000">
                </div>
                
                <button class="launch-btn" id="launch-btn">
                    <span class="btn-icon">▶</span>
                    Launch Content Arbitrage
                </button>
                
                <div class="mock-toggle">
                    <label>
                        <input type="checkbox" id="use-mock" checked>
                        Use mock mode (safe fallback)
                    </label>
                </div>
            </div>
            
            <!-- Active Run Status -->
            <div class="run-status" id="run-status" style="display: none;">
                <div class="progress-header">
                    <span class="run-id" id="run-id-display"></span>
                    <span class="status-badge" id="status-badge">RUNNING</span>
                </div>
                
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
                </div>
                
                <div class="current-step" id="current-step">Initializing...</div>
                
                <!-- Virtual Agents -->
                <div class="virtual-agents" id="virtual-agents">
                    <div class="agent-slot" data-agent="scout">
                        <div class="agent-avatar" style="background: #00f3ff;">🔍</div>
                        <div class="agent-info">
                            <span class="agent-name">Scout</span>
                            <span class="agent-status" id="scout-status">idle</span>
                        </div>
                    </div>
                    <div class="agent-slot" data-agent="maker">
                        <div class="agent-avatar" style="background: #ff006e;">✍️</div>
                        <div class="agent-info">
                            <span class="agent-name">Maker</span>
                            <span class="agent-status" id="maker-status">idle</span>
                        </div>
                    </div>
                    <div class="agent-slot" data-agent="merchant">
                        <div class="agent-avatar" style="background: #39ff14;">🏪</div>
                        <div class="agent-info">
                            <span class="agent-name">Merchant</span>
                            <span class="agent-status" id="merchant-status">idle</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Results Section -->
            <div class="results-section" id="results-section" style="display: none;">
                <h4>✅ Workflow Complete</h4>
                
                <div class="result-item">
                    <span class="result-label">Platform:</span>
                    <span class="result-value" id="result-platform">-</span>
                </div>
                
                <div class="result-item">
                    <span class="result-label">Revenue:</span>
                    <span class="result-value revenue" id="result-revenue">$-</span>
                </div>
                
                <div class="result-item">
                    <span class="result-label">URL:</span>
                    <a class="result-link" id="result-url" href="#" target="_blank">View Content</a>
                </div>
                
                <button class="launch-btn secondary" id="launch-another-btn">
                    Launch Another
                </button>
            </div>
            
            <!-- Run History -->
            <div class="history-section">
                <h4>📜 Recent Runs</h4>
                <div class="history-list" id="history-list">
                    <p class="empty-history">No runs yet</p>
                </div>
            </div>
            
            <!-- Event Log -->
            <div class="event-log" id="event-log" style="display: none;">
                <h4>📋 Event Log</h4>
                <div class="event-list" id="event-list"></div>
            </div>
        `;
        
        // Add to UI layer
        const uiLayer = document.getElementById('ui-layer');
        if (uiLayer) {
            uiLayer.appendChild(panel);
        } else {
            document.body.appendChild(panel);
        }
        
        this.panel = panel;
    }
    
    injectStyles() {
        const styles = document.createElement('style');
        styles.textContent = `
            .workflow-panel {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 320px;
                max-height: 90vh;
                background: rgba(10, 22, 40, 0.95);
                border: 1px solid #00f3ff;
                border-radius: 12px;
                padding: 20px;
                color: #e0e1dd;
                font-family: 'Rajdhani', 'Segoe UI', sans-serif;
                overflow-y: auto;
                z-index: 100;
                box-shadow: 0 0 40px rgba(0, 243, 255, 0.15);
                backdrop-filter: blur(10px);
            }
            
            .workflow-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid rgba(0, 243, 255, 0.3);
            }
            
            .workflow-header h3 {
                margin: 0;
                font-size: 16px;
                color: #00f3ff;
            }
            
            .engine-badge {
                font-size: 10px;
                padding: 3px 8px;
                border-radius: 4px;
                background: #39ff14;
                color: #000;
                font-weight: bold;
            }
            
            .engine-badge.mock {
                background: #ffb347;
            }
            
            .binding-status {
                padding: 10px;
                background: rgba(0, 243, 255, 0.1);
                border-radius: 6px;
                margin-bottom: 15px;
            }
            
            .binding-status.bound {
                background: rgba(57, 255, 20, 0.1);
                border: 1px solid #39ff14;
            }
            
            .input-group {
                margin-bottom: 12px;
            }
            
            .input-group label {
                display: block;
                font-size: 12px;
                color: #8892a0;
                margin-bottom: 4px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .input-group input,
            .input-group select {
                width: 100%;
                padding: 8px 12px;
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid #2a3f5f;
                border-radius: 6px;
                color: #e0e1dd;
                font-size: 14px;
            }
            
            .input-group input:focus,
            .input-group select:focus {
                outline: none;
                border-color: #00f3ff;
            }
            
            .launch-btn {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #00f3ff, #00a8ff);
                border: none;
                border-radius: 8px;
                color: #000;
                font-weight: bold;
                font-size: 14px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                transition: all 0.3s ease;
            }
            
            .launch-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(0, 243, 255, 0.4);
            }
            
            .launch-btn:disabled {
                background: #2a3f5f;
                color: #8892a0;
                cursor: not-allowed;
                transform: none;
            }
            
            .launch-btn.secondary {
                background: transparent;
                border: 1px solid #00f3ff;
                color: #00f3ff;
            }
            
            .btn-icon {
                font-size: 12px;
            }
            
            .mock-toggle {
                margin-top: 10px;
                font-size: 12px;
                color: #8892a0;
            }
            
            .mock-toggle input {
                margin-right: 5px;
            }
            
            .progress-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                font-size: 12px;
            }
            
            .run-id {
                color: #8892a0;
                font-family: monospace;
            }
            
            .status-badge {
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                background: #ffb347;
                color: #000;
            }
            
            .status-badge.completed {
                background: #39ff14;
            }
            
            .status-badge.failed {
                background: #ff006e;
                color: #fff;
            }
            
            .progress-bar-container {
                height: 6px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 3px;
                overflow: hidden;
                margin-bottom: 10px;
            }
            
            .progress-bar {
                height: 100%;
                background: linear-gradient(90deg, #00f3ff, #39ff14);
                transition: width 0.5s ease;
            }
            
            .current-step {
                font-size: 13px;
                color: #00f3ff;
                text-align: center;
                margin-bottom: 15px;
            }
            
            .virtual-agents {
                display: flex;
                justify-content: space-between;
                gap: 8px;
                margin-bottom: 15px;
            }
            
            .agent-slot {
                flex: 1;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 10px 5px;
                text-align: center;
                border: 1px solid transparent;
                transition: all 0.3s ease;
            }
            
            .agent-slot.active {
                border-color: #00f3ff;
                box-shadow: 0 0 15px rgba(0, 243, 255, 0.3);
            }
            
            .agent-slot.completed {
                border-color: #39ff14;
            }
            
            .agent-avatar {
                width: 36px;
                height: 36px;
                border-radius: 50%;
                margin: 0 auto 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
            }
            
            .agent-info {
                display: flex;
                flex-direction: column;
                gap: 2px;
            }
            
            .agent-name {
                font-size: 11px;
                font-weight: bold;
            }
            
            .agent-status {
                font-size: 9px;
                color: #8892a0;
                text-transform: uppercase;
            }
            
            .results-section {
                background: rgba(57, 255, 20, 0.1);
                border: 1px solid #39ff14;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
            }
            
            .results-section h4 {
                margin: 0 0 12px 0;
                color: #39ff14;
            }
            
            .result-item {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                font-size: 13px;
            }
            
            .result-label {
                color: #8892a0;
            }
            
            .result-value {
                font-weight: bold;
            }
            
            .result-value.revenue {
                color: #39ff14;
                font-size: 18px;
            }
            
            .result-link {
                color: #00f3ff;
                text-decoration: none;
            }
            
            .result-link:hover {
                text-decoration: underline;
            }
            
            .history-section {
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .history-section h4 {
                margin: 0 0 10px 0;
                font-size: 13px;
                color: #8892a0;
            }
            
            .history-list {
                max-height: 120px;
                overflow-y: auto;
            }
            
            .history-item {
                display: flex;
                justify-content: space-between;
                padding: 8px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                margin-bottom: 5px;
                font-size: 12px;
            }
            
            .history-item.completed {
                border-left: 2px solid #39ff14;
            }
            
            .history-item.failed {
                border-left: 2px solid #ff006e;
            }
            
            .empty-history {
                text-align: center;
                color: #8892a0;
                font-size: 12px;
                padding: 20px;
            }
            
            .event-log {
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .event-log h4 {
                margin: 0 0 10px 0;
                font-size: 13px;
                color: #8892a0;
            }
            
            .event-list {
                max-height: 150px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 11px;
            }
            
            .event-item {
                padding: 4px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                color: #8892a0;
            }
            
            .event-item:last-child {
                border-bottom: none;
            }
        `;
        document.head.appendChild(styles);
    }
    
    attachEventListeners() {
        // Launch button
        const launchBtn = document.getElementById('launch-btn');
        if (launchBtn) {
            launchBtn.addEventListener('click', () => this.onLaunchClick());
        }
        
        // Launch another button
        const launchAnotherBtn = document.getElementById('launch-another-btn');
        if (launchAnotherBtn) {
            launchAnotherBtn.addEventListener('click', () => this.resetForNewRun());
        }
        
        // Engine badge toggle (for debugging)
        const engineBadge = document.getElementById('engine-badge');
        if (engineBadge) {
            engineBadge.addEventListener('click', () => this.toggleEngineMode());
        }
    }
    
    // ============== Public API ==============
    
    setCurrentRoom(roomId) {
        this.currentRoomId = roomId;
        console.log(`🏠 RoomWorkflowPanel: Active room set to ${roomId}`);
        this.checkRoomBinding();
    }
    
    // ============== Binding Management ==============
    
    async checkRoomBinding() {
        if (!this.currentRoomId) return;
        
        const statusEl = document.getElementById('binding-status');
        const launchSection = document.getElementById('launch-section');
        
        try {
            // In production, this would call: GET /api/rooms/{id}/engine
            // For now, simulate bound state
            const binding = {
                isBound: true,
                engineType: 'chatdev-money',
                workflowId: 'content_arbitrage_v1',
                useMockFallback: true
            };
            
            if (binding.isBound) {
                statusEl.innerHTML = `
                    <p class="status-text">✅ Room bound to <strong>${binding.workflowId}</strong></p>
                    <p class="status-sub">Engine: ${binding.engineType}</p>
                `;
                statusEl.classList.add('bound');
                launchSection.style.display = 'block';
                
                // Update engine badge
                const badge = document.getElementById('engine-badge');
                badge.textContent = binding.useMockFallback ? 'MOCK' : 'LIVE';
                badge.classList.toggle('mock', binding.useMockFallback);
            } else {
                statusEl.innerHTML = `
                    <p class="status-text">⚠️ Room not bound to any workflow</p>
                    <button class="launch-btn" onclick="bindRoom()">Bind Now</button>
                `;
                launchSection.style.display = 'none';
            }
            
        } catch (error) {
            statusEl.innerHTML = `<p class="status-text error">❌ Error: ${error.message}</p>`;
        }
    }
    
    // ============== Workflow Launch ==============
    
    async onLaunchClick() {
        const launchBtn = document.getElementById('launch-btn');
        const subreddit = document.getElementById('subreddit-input').value;
        const minUpvotes = document.getElementById('upvotes-input').value;
        const useMock = document.getElementById('use-mock').checked;
        
        launchBtn.disabled = true;
        launchBtn.innerHTML = '<span class="btn-icon">⏳</span> Launching...';
        
        try {
            const result = await this.launchWorkflow({
                subreddit,
                minUpvotes: parseInt(minUpvotes),
                useMock
            });
            
            this.activeRunId = result.run_id;
            this.showRunStatus(result);
            this.startPolling();
            
        } catch (error) {
            console.error('Launch failed:', error);
            launchBtn.disabled = false;
            launchBtn.innerHTML = '<span class="btn-icon">❌</span> Failed - Retry';
        }
    }
    
    async launchWorkflow(inputs) {
        // In production: POST /api/rooms/{id}/workflows/launch
        // For demo, call the adapter directly
        
        const response = await fetch(`${this.adapterUrl}/prototype/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_id: this.currentRoomId || 'demo-room',
                user_id: 'current-user',
                workflow_id: 'content_arbitrage_v1',
                subreddit: inputs.subreddit,
                min_upvotes: inputs.minUpvotes,
                use_mock: inputs.useMock
            })
        });
        
        if (!response.ok) {
            throw new Error(`Launch failed: ${response.status}`);
        }
        
        return await response.json();
    }
    
    // ============== Status & Polling ==============
    
    showRunStatus(result) {
        document.getElementById('launch-section').style.display = 'none';
        document.getElementById('run-status').style.display = 'block';
        document.getElementById('event-log').style.display = 'block';
        
        document.getElementById('run-id-display').textContent = result.run_id.substring(0, 12);
        document.getElementById('status-badge').textContent = result.status.toUpperCase();
        
        this.addEventToLog(`Workflow started: ${result.run_id}`);
    }
    
    startPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        
        this.pollingInterval = setInterval(() => this.pollStatus(), 1000);
    }
    
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
    
    async pollStatus() {
        if (!this.activeRunId) return;
        
        try {
            const response = await fetch(`${this.adapterUrl}/prototype/status/${this.activeRunId}`);
            const status = await response.json();
            
            this.updateStatusUI(status);
            
            if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
                this.stopPolling();
                this.onWorkflowComplete(status);
            }
            
        } catch (error) {
            console.error('Polling error:', error);
        }
    }
    
    updateStatusUI(status) {
        // Update progress bar
        const progressBar = document.getElementById('progress-bar');
        progressBar.style.width = `${status.progress || 0}%`;
        
        // Update step text
        const stepEl = document.getElementById('current-step');
        if (status.current_step) {
            stepEl.textContent = `Current: ${status.current_step}`;
        }
        
        // Update status badge
        const badge = document.getElementById('status-badge');
        badge.textContent = (status.status || 'unknown').toUpperCase();
        badge.className = 'status-badge ' + status.status;
        
        // Update virtual agents
        this.updateVirtualAgents(status);
        
        // Add events to log
        if (status.events) {
            const lastEvent = status.events[status.events.length - 1];
            if (lastEvent && lastEvent.event_name) {
                this.addEventToLog(`${lastEvent.event_name}: ${JSON.stringify(lastEvent.payload || {})}`);
            }
        }
    }
    
    updateVirtualAgents(status) {
        // Map current step to agent
        const stepToAgent = {
            'Scout': 'scout',
            'Maker': 'maker',
            'Merchant': 'merchant'
        };
        
        // Reset all agents
        document.querySelectorAll('.agent-slot').forEach(slot => {
            slot.classList.remove('active', 'completed');
        });
        
        // Update based on progress
        const progress = status.progress || 0;
        
        if (progress >= 33) {
            document.querySelector('[data-agent="scout"]').classList.add('completed');
            document.getElementById('scout-status').textContent = 'completed';
        }
        if (progress >= 66) {
            document.querySelector('[data-agent="maker"]').classList.add('completed');
            document.getElementById('maker-status').textContent = 'completed';
        }
        if (progress >= 100) {
            document.querySelector('[data-agent="merchant"]').classList.add('completed');
            document.getElementById('merchant-status').textContent = 'completed';
        }
        
        // Mark current agent as active
        const currentStep = status.current_step;
        if (currentStep && stepToAgent[currentStep] && progress < 100) {
            const agentKey = stepToAgent[currentStep];
            document.querySelector(`[data-agent="${agentKey}"]`).classList.add('active');
            document.getElementById(`${agentKey}-status`).textContent = 'working';
        }
    }
    
    // ============== Completion ==============
    
    onWorkflowComplete(status) {
        document.getElementById('run-status').style.display = 'none';
        document.getElementById('results-section').style.display = 'block';
        
        const outputs = status.outputs || {};
        
        document.getElementById('result-platform').textContent = outputs.platform || '-';
        document.getElementById('result-revenue').textContent = `$${outputs.estimated_revenue || 0}`;
        
        const urlEl = document.getElementById('result-url');
        if (outputs.published_url) {
            urlEl.href = outputs.published_url;
            urlEl.textContent = 'View Published Content →';
        } else {
            urlEl.textContent = 'No URL available';
            urlEl.href = '#';
        }
        
        this.addEventToLog('✅ Workflow completed successfully');
        this.addToHistory(status);
    }
    
    addToHistory(status) {
        const historyList = document.getElementById('history-list');
        const emptyMsg = historyList.querySelector('.empty-history');
        if (emptyMsg) emptyMsg.remove();
        
        const outputs = status.outputs || {};
        const date = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        const item = document.createElement('div');
        item.className = `history-item ${status.status}`;
        item.innerHTML = `
            <span>Run #${historyList.children.length + 1} - ${date}</span>
            <span>${outputs.estimated_revenue ? '$' + outputs.estimated_revenue : status.status}</span>
        `;
        
        historyList.insertBefore(item, historyList.firstChild);
    }
    
    resetForNewRun() {
        this.activeRunId = null;
        document.getElementById('results-section').style.display = 'none';
        document.getElementById('launch-section').style.display = 'block';
        document.getElementById('event-log').style.display = 'none';
        
        const launchBtn = document.getElementById('launch-btn');
        launchBtn.disabled = false;
        launchBtn.innerHTML = '<span class="btn-icon">▶</span> Launch Content Arbitrage';
        
        // Reset progress
        document.getElementById('progress-bar').style.width = '0%';
        document.getElementById('event-list').innerHTML = '';
        
        // Reset agents
        document.querySelectorAll('.agent-slot').forEach(slot => {
            slot.classList.remove('active', 'completed');
        });
        ['scout', 'maker', 'merchant'].forEach(agent => {
            document.getElementById(`${agent}-status`).textContent = 'idle';
        });
    }
    
    // ============== Utilities ==============
    
    addEventToLog(message) {
        const eventList = document.getElementById('event-list');
        const item = document.createElement('div');
        item.className = 'event-item';
        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        item.textContent = `[${time}] ${message}`;
        eventList.appendChild(item);
        eventList.scrollTop = eventList.scrollHeight;
    }
    
    toggleEngineMode() {
        // For debugging: toggle between mock and real
        const badge = document.getElementById('engine-badge');
        const isMock = badge.textContent === 'MOCK';
        badge.textContent = isMock ? 'LIVE' : 'MOCK';
        badge.classList.toggle('mock', !isMock);
        console.log(`Engine mode: ${isMock ? 'LIVE' : 'MOCK'}`);
    }
}

// Export for use in game.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RoomWorkflowPanel;
}
