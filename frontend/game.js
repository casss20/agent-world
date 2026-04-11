// Agent World - Three.js Frontend
// Real-time 3D visualization of AI agents

class AgentWorld3D {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.agents = new Map();
        this.rooms = new Map();
        this.selectedAgent = null;
        this.ws = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.taskCount = 0;
        
        this.init();
    }
    
    init() {
        this.setupScene();
        this.setupLights();
        this.setupCamera();
        this.setupRenderer();
        this.setupControls();
        this.setupEventListeners();
        this.connectWebSocket();
        this.animate();
    }
    
    setupScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x050a14);
        this.scene.fog = new THREE.FogExp2(0x050a14, 0.02);
    }
    
    setupLights() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambientLight);
        
        // Main directional light (cyberpunk cyan)
        const dirLight = new THREE.DirectionalLight(0x00f3ff, 0.5);
        dirLight.position.set(10, 20, 10);
        this.scene.add(dirLight);
        
        // Accent lights for atmosphere
        const colors = [0xff006e, 0x39ff14, 0xffb347];
        colors.forEach((color, i) => {
            const light = new THREE.PointLight(color, 0.3, 20);
            light.position.set(
                Math.sin(i * 2.09) * 8,
                5,
                Math.cos(i * 2.09) * 8
            );
            this.scene.add(light);
        });
    }
    
    setupCamera() {
        this.camera = new THREE.PerspectiveCamera(
            60,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 12, 15);
        this.camera.lookAt(0, 0, 0);
    }
    
    setupRenderer() {
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        document.getElementById('canvas-container').appendChild(this.renderer.domElement);
    }
    
    setupControls() {
        // Simple orbit controls (mouse drag to rotate)
        this.isDragging = false;
        this.previousMousePosition = { x: 0, y: 0 };
        this.cameraAngle = 0;
        this.cameraRadius = 15;
        this.cameraHeight = 12;
    }
    
    setupEventListeners() {
        window.addEventListener('resize', () => this.onWindowResize(), false);
        
        // Mouse events for interaction
        this.renderer.domElement.addEventListener('mousedown', (e) => this.onMouseDown(e), false);
        this.renderer.domElement.addEventListener('mousemove', (e) => this.onMouseMove(e), false);
        this.renderer.domElement.addEventListener('mouseup', () => this.onMouseUp(), false);
        this.renderer.domElement.addEventListener('click', (e) => this.onClick(e), false);
        
        // Touch support
        this.renderer.domElement.addEventListener('touchstart', (e) => this.onTouchStart(e), false);
        this.renderer.domElement.addEventListener('touchmove', (e) => this.onTouchMove(e), false);
        this.renderer.domElement.addEventListener('touchend', () => this.onMouseUp(), false);
    }
    
    connectWebSocket() {
        const wsUrl = window.location.protocol === 'https:' 
            ? `wss://${window.location.host}/ws/world`
            : `ws://localhost:8000/ws/world`;
            
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('Connected to Agent World');
            document.getElementById('loading').classList.add('hidden');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleServerMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('Disconnected, retrying...');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    handleServerMessage(data) {
        switch(data.type) {
            case 'world_init':
                this.initializeWorld(data);
                break;
            case 'agent_moved':
                this.moveAgent(data.agent_id, data.to_room);
                break;
            case 'agent_progress':
                this.updateAgentProgress(data.agent_id, data.progress, data.log);
                break;
            case 'task_completed':
                this.taskCount++;
                document.getElementById('stat-tasks').textContent = this.taskCount;
                break;
            case 'agent_spawned':
                this.createAgent3D(data.agent);
                break;
            case 'agent_paused':
                this.updateAgentStatus(data.agent_id, 'paused');
                break;
            case 'agent_activity':
                console.log(data.agent_id, data.message);
                break;
        }
    }
    
    initializeWorld(data) {
        // Create rooms
        data.rooms.forEach(roomData => {
            this.createRoom3D(roomData);
        });
        
        // Create agents
        data.agents.forEach(agentData => {
            this.createAgent3D(agentData);
        });
        
        // Update stats
        document.getElementById('stat-agents').textContent = data.agents.length;
        document.getElementById('stat-rooms').textContent = data.rooms.length;
        
        // Update room list UI
        this.updateRoomList(data.rooms);
    }
    
    createRoom3D(roomData) {
        const group = new THREE.Group();
        
        // Room platform
        const geometry = new THREE.CylinderGeometry(3, 3.5, 0.5, 8);
        const material = new THREE.MeshPhongMaterial({
            color: roomData.color || 0x1a1c2c,
            emissive: roomData.color || 0x1a1c2c,
            emissiveIntensity: 0.2,
            transparent: true,
            opacity: 0.9
        });
        const platform = new THREE.Mesh(geometry, material);
        platform.position.y = -0.25;
        platform.receiveShadow = true;
        group.add(platform);
        
        // Glowing ring
        const ringGeo = new THREE.TorusGeometry(3.2, 0.1, 16, 100);
        const ringMat = new THREE.MeshBasicMaterial({ 
            color: 0x00f3ff,
            transparent: true,
            opacity: 0.5
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.1;
        group.add(ring);
        
        // Room label
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'rgba(0, 0, 0, 0)';
        ctx.fillRect(0, 0, 256, 64);
        ctx.font = 'bold 24px Orbitron';
        ctx.fillStyle = '#00f3ff';
        ctx.textAlign = 'center';
        ctx.fillText(roomData.name.toUpperCase(), 128, 40);
        
        const texture = new THREE.CanvasTexture(canvas);
        const labelGeo = new THREE.PlaneGeometry(3, 0.75);
        const labelMat = new THREE.MeshBasicMaterial({ 
            map: texture, 
            transparent: true,
            side: THREE.DoubleSide
        });
        const label = new THREE.Mesh(labelGeo, labelMat);
        label.position.set(0, 3.5, 0);
        label.lookAt(0, 3.5, 5);
        group.add(label);
        
        group.position.set(roomData.x, 0, roomData.y);
        this.scene.add(group);
        
        this.rooms.set(roomData.id, {
            data: roomData,
            mesh: group,
            agents: roomData.agents || []
        });
    }
    
    createAgent3D(agentData) {
        const group = new THREE.Group();
        
        // Agent body (glowing orb)
        const geometry = new THREE.SphereGeometry(0.4, 32, 32);
        const material = new THREE.MeshPhongMaterial({
            color: agentData.avatar_color || 0x00f3ff,
            emissive: agentData.avatar_color || 0x00f3ff,
            emissiveIntensity: 0.5
        });
        const body = new THREE.Mesh(geometry, material);
        body.castShadow = true;
        group.add(body);
        
        // Outer glow
        const glowGeo = new THREE.SphereGeometry(0.6, 32, 32);
        const glowMat = new THREE.MeshBasicMaterial({
            color: agentData.avatar_color || 0x00f3ff,
            transparent: true,
            opacity: 0.2
        });
        const glow = new THREE.Mesh(glowGeo, glowMat);
        group.add(glow);
        
        // Status indicator ring
        const ringGeo = new THREE.RingGeometry(0.5, 0.55, 32);
        const ringMat = new THREE.MeshBasicMaterial({
            color: this.getStatusColor(agentData.status),
            transparent: true,
            opacity: 0.8,
            side: THREE.DoubleSide
        });
        const statusRing = new THREE.Mesh(ringGeo, ringMat);
        statusRing.rotation.x = -Math.PI / 2;
        statusRing.position.y = -0.3;
        group.add(statusRing);
        
        // Position in room
        const room = this.rooms.get(agentData.room_id);
        if (room) {
            const angle = (room.agents.length * 60) * (Math.PI / 180);
            const radius = 1.5;
            group.position.set(
                room.data.x + Math.cos(angle) * radius,
                0.4,
                room.data.y + Math.sin(angle) * radius
            );
            room.agents.push(agentData.id);
        }
        
        // Add floating animation
        group.userData = {
            agentId: agentData.id,
            originalY: 0.4,
            floatOffset: Math.random() * Math.PI * 2,
            statusRing: statusRing
        };
        
        this.scene.add(group);
        this.agents.set(agentData.id, {
            data: agentData,
            mesh: group,
            currentRoom: agentData.room_id
        });
    }
    
    getStatusColor(status) {
        const colors = {
            'idle': 0x39ff14,
            'working': 0xffa500,
            'paused': 0xff4444,
            'error': 0xff0000
        };
        return colors[status] || 0x808080;
    }
    
    moveAgent(agentId, toRoomId) {
        const agent = this.agents.get(agentId);
        if (!agent) return;
        
        const fromRoom = this.rooms.get(agent.currentRoom);
        const toRoom = this.rooms.get(toRoomId);
        
        if (fromRoom && toRoom) {
            // Remove from old room
            fromRoom.agents = fromRoom.agents.filter(id => id !== agentId);
            
            // Calculate new position
            const angle = (toRoom.agents.length * 60) * (Math.PI / 180);
            const radius = 1.5;
            const targetX = toRoom.data.x + Math.cos(angle) * radius;
            const targetZ = toRoom.data.y + Math.sin(angle) * radius;
            
            // Animate movement
            this.animateAgentMove(agent.mesh, targetX, targetZ);
            
            // Update data
            toRoom.agents.push(agentId);
            agent.currentRoom = toRoomId;
            agent.data.room_id = toRoomId;
            
            // Update UI if selected
            if (this.selectedAgent === agentId) {
                this.showAgentDetails(agentId);
            }
        }
    }
    
    animateAgentMove(mesh, targetX, targetZ) {
        const startX = mesh.position.x;
        const startZ = mesh.position.z;
        const duration = 1000;
        const startTime = Date.now();
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Ease out
            const ease = 1 - Math.pow(1 - progress, 3);
            
            mesh.position.x = startX + (targetX - startX) * ease;
            mesh.position.z = startZ + (targetZ - startZ) * ease;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        animate();
    }
    
    updateAgentProgress(agentId, progress, log) {
        const agent = this.agents.get(agentId);
        if (!agent) return;
        
        agent.data.progress = progress;
        
        // Update UI if this agent is selected
        if (this.selectedAgent === agentId) {
            document.getElementById('agent-progress').style.width = progress + '%';
            
            if (log) {
                const logsContainer = document.getElementById('agent-logs');
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                entry.innerHTML = `<span class="log-time">${new Date().toLocaleTimeString()}</span> ${log}`;
                logsContainer.insertBefore(entry, logsContainer.firstChild);
            }
        }
    }
    
    updateAgentStatus(agentId, status) {
        const agent = this.agents.get(agentId);
        if (!agent) return;
        
        agent.data.status = status;
        
        // Update 3D status ring
        const statusRing = agent.mesh.userData.statusRing;
        if (statusRing) {
            statusRing.material.color.setHex(this.getStatusColor(status));
        }
        
        // Update UI
        if (this.selectedAgent === agentId) {
            const statusBadge = document.getElementById('agent-status');
            statusBadge.textContent = status.toUpperCase();
            statusBadge.className = 'status-badge status-' + status;
        }
    }
    
    updateRoomList(rooms) {
        const container = document.getElementById('rooms-container');
        container.innerHTML = '';
        
        rooms.forEach(room => {
            const div = document.createElement('div');
            div.className = 'room-item';
            div.innerHTML = `
                <div class="room-name">◆ ${room.name}</div>
                <div class="room-agents">${room.agents?.length || 0} agents present</div>
            `;
            div.onclick = () => this.focusOnRoom(room.id);
            container.appendChild(div);
        });
    }
    
    focusOnRoom(roomId) {
        const room = this.rooms.get(roomId);
        if (!room) return;
        
        // Animate camera to room
        const targetX = room.data.x;
        const targetZ = room.data.y + 8;
        
        // Simple camera animation
        const startX = this.camera.position.x;
        const startZ = this.camera.position.z;
        const duration = 1000;
        const startTime = Date.now();
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const ease = 1 - Math.pow(1 - progress, 3);
            
            this.camera.position.x = startX + (targetX - startX) * ease;
            this.camera.position.z = startZ + (targetZ - startZ) * ease;
            this.camera.lookAt(room.data.x, 0, room.data.y);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        animate();
    }
    
    onMouseDown(event) {
        this.isDragging = true;
        this.previousMousePosition = {
            x: event.clientX,
            y: event.clientY
        };
    }
    
    onMouseMove(event) {
        if (this.isDragging) {
            const deltaX = event.clientX - this.previousMousePosition.x;
            this.cameraAngle -= deltaX * 0.01;
            
            this.camera.position.x = Math.sin(this.cameraAngle) * this.cameraRadius;
            this.camera.position.z = Math.cos(this.cameraAngle) * this.cameraRadius;
            this.camera.lookAt(0, 0, 0);
            
            this.previousMousePosition = {
                x: event.clientX,
                y: event.clientY
            };
        }
        
        // Update mouse for raycasting
        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    }
    
    onMouseUp() {
        this.isDragging = false;
    }
    
    onClick(event) {
        if (this.isDragging) return;
        
        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        // Check for agent clicks
        const agentMeshes = Array.from(this.agents.values()).map(a => a.mesh);
        const intersects = this.raycaster.intersectObjects(agentMeshes, true);
        
        if (intersects.length > 0) {
            // Find the agent group
            let obj = intersects[0].object;
            while (obj.parent && !obj.userData.agentId) {
                obj = obj.parent;
            }
            
            if (obj.userData.agentId) {
                this.selectAgent(obj.userData.agentId);
            }
        }
    }
    
    onTouchStart(event) {
        if (event.touches.length === 1) {
            this.onMouseDown(event.touches[0]);
        }
    }
    
    onTouchMove(event) {
        if (event.touches.length === 1) {
            event.preventDefault();
            this.onMouseMove(event.touches[0]);
        }
    }
    
    selectAgent(agentId) {
        this.selectedAgent = agentId;
        const agent = this.agents.get(agentId);
        if (!agent) return;
        
        // Show panel
        document.getElementById('agent-panel').classList.add('active');
        
        // Update details
        this.showAgentDetails(agentId);
    }
    
    showAgentDetails(agentId) {
        const agent = this.agents.get(agentId);
        if (!agent) return;
        
        document.getElementById('agent-name').textContent = agent.data.name;
        document.getElementById('agent-role').textContent = agent.data.role;
        document.getElementById('agent-avatar').textContent = 
            agent.data.role === 'Researcher' ? '🔍' :
            agent.data.role === 'Designer' ? '🎨' :
            agent.data.role === 'Writer' ? '✍️' : '🤖';
        document.getElementById('agent-avatar').style.borderColor = agent.data.avatar_color;
        
        const statusBadge = document.getElementById('agent-status');
        statusBadge.textContent = agent.data.status.toUpperCase();
        statusBadge.className = 'status-badge status-' + agent.data.status;
        
        document.getElementById('agent-progress').style.width = (agent.data.progress || 0) + '%';
    }
    
    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        // Float animation for agents
        const time = Date.now() * 0.001;
        this.agents.forEach(agent => {
            const mesh = agent.mesh;
            const offset = mesh.userData.floatOffset || 0;
            mesh.position.y = mesh.userData.originalY + Math.sin(time + offset) * 0.1;
            mesh.rotation.y = Math.sin(time * 0.5 + offset) * 0.1;
        });
        
        // Rotate room rings
        this.rooms.forEach(room => {
            const ring = room.mesh.children[1];
            if (ring) {
                ring.rotation.z += 0.005;
            }
        });
        
        this.renderer.render(this.scene, this.camera);
    }
}

// UI Functions
function openModal() {
    document.getElementById('modal').classList.add('active');
}

function closeModal() {
    document.getElementById('modal').classList.remove('active');
}

function createAgent() {
    const name = document.getElementById('new-agent-name').value || `Agent ${game.agents.size + 1}`;
    const role = document.getElementById('new-agent-role').value;
    
    if (game.ws && game.ws.readyState === WebSocket.OPEN) {
        game.ws.send(JSON.stringify({
            action: 'spawn_agent',
            name: name,
            role: role
        }));
    }
    
    closeModal();
    document.getElementById('new-agent-name').value = '';
}

function assignTask() {
    if (!game.selectedAgent) return;
    
    const taskTypes = ['research', 'design', 'write', 'analyze'];
    const taskType = taskTypes[Math.floor(Math.random() * taskTypes.length)];
    
    if (game.ws && game.ws.readyState === WebSocket.OPEN) {
        game.ws.send(JSON.stringify({
            action: 'assign_task',
            agent_id: game.selectedAgent,
            task_type: taskType,
            description: `Perform ${taskType} task`
        }));
    }
}

function pauseAgent() {
    if (!game.selectedAgent) return;
    
    if (game.ws && game.ws.readyState === WebSocket.OPEN) {
        game.ws.send(JSON.stringify({
            action: 'pause_agent',
            agent_id: game.selectedAgent
        }));
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.game = new AgentWorld3D();
    
    // Initialize workflow panel (Ticket 8)
    window.workflowPanel = new RoomWorkflowPanel(window.game);
    
    // Set current room when game loads
    // In production, this would come from URL or navigation
    window.workflowPanel.setCurrentRoom('demo-room-001');
});
