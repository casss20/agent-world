#!/bin/bash

echo "🚀 Starting Agent World..."

# Start backend in background
echo "📡 Starting backend..."
cd backend
python -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -q -r requirements.txt
python main.py &
BACKEND_PID=$!

cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo "🎮 Starting frontend..."
cd frontend
python -m http.server 8080 &
FRONTEND_PID=$!

echo ""
echo "✅ Agent World is running!"
echo ""
echo "🌐 Open: http://localhost:8080"
echo "📊 API:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
