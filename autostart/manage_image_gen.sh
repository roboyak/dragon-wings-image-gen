#!/bin/bash
# Dragon Wings Image Generator - Service Management
# Manages both backend (FastAPI) and frontend (Rails) services

LOG_DIR="/opt/dragon/logs"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# PID files
BACKEND_PID="$LOG_DIR/image_gen_backend.pid"
FRONTEND_PID="$LOG_DIR/image_gen_frontend.pid"

case "$1" in
    start)
        echo "Starting Image Generator services..."
        echo ""

        # Start backend first
        echo "[1/2] Starting backend (FastAPI)..."
        "$SCRIPT_DIR/start_backend.sh"

        # Wait for backend to initialize
        sleep 5

        # Start frontend
        echo "[2/2] Starting frontend (Rails)..."
        "$SCRIPT_DIR/start_frontend.sh"

        echo ""
        echo "✅ All Image Generator services started"
        ;;

    stop)
        echo "Stopping Image Generator services..."
        echo ""

        # Stop frontend first
        if [ -f "$FRONTEND_PID" ]; then
            PID=$(cat "$FRONTEND_PID")
            echo "Stopping frontend (PID: $PID)..."
            kill "$PID" 2>/dev/null
            rm "$FRONTEND_PID"
        fi

        # Stop backend
        if [ -f "$BACKEND_PID" ]; then
            PID=$(cat "$BACKEND_PID")
            echo "Stopping backend (PID: $PID)..."
            kill "$PID" 2>/dev/null
            rm "$BACKEND_PID"
        fi

        echo ""
        echo "✅ All Image Generator services stopped"
        ;;

    restart)
        $0 stop
        sleep 3
        $0 start
        ;;

    status)
        echo "Image Generator Service Status"
        echo "======================================================================"
        echo ""

        # Check backend
        if [ -f "$BACKEND_PID" ]; then
            PID=$(cat "$BACKEND_PID")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "✅ Backend running (PID: $PID) - Port 8000"
                # Check if responding
                if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
                    echo "   Status: Responding to health checks"
                fi
            else
                echo "❌ Backend NOT running (PID $PID not found)"
            fi
        else
            echo "❌ Backend NOT running (no PID file)"
        fi

        # Check frontend
        if [ -f "$FRONTEND_PID" ]; then
            PID=$(cat "$FRONTEND_PID")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "✅ Frontend running (PID: $PID) - Port 3000"
                # Check if responding
                if curl -s http://localhost:3000/up > /dev/null 2>&1; then
                    echo "   Status: Responding to health checks"
                fi
            else
                echo "❌ Frontend NOT running (PID $PID not found)"
            fi
        else
            echo "❌ Frontend NOT running (no PID file)"
        fi

        # Show log stats
        echo ""
        echo "Logs:"
        if [ -f "$LOG_DIR/image_gen_backend.log" ]; then
            LINES=$(wc -l < "$LOG_DIR/image_gen_backend.log")
            echo "  Backend:  $LINES lines"
        fi
        if [ -f "$LOG_DIR/image_gen_frontend.log" ]; then
            LINES=$(wc -l < "$LOG_DIR/image_gen_frontend.log")
            echo "  Frontend: $LINES lines"
        fi
        ;;

    logs)
        case "$2" in
            backend)
                tail -f "$LOG_DIR/image_gen_backend.log"
                ;;
            frontend)
                tail -f "$LOG_DIR/image_gen_frontend.log"
                ;;
            *)
                # Show both
                echo "=== Backend Log (last 10 lines) ==="
                tail -10 "$LOG_DIR/image_gen_backend.log" 2>/dev/null || echo "(no log yet)"
                echo ""
                echo "=== Frontend Log (last 10 lines) ==="
                tail -10 "$LOG_DIR/image_gen_frontend.log" 2>/dev/null || echo "(no log yet)"
                ;;
        esac
        ;;

    *)
        echo "Dragon Wings Image Generator - Service Management"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs [backend|frontend]}"
        echo ""
        echo "Commands:"
        echo "  start   - Start both backend and frontend"
        echo "  stop    - Stop both services"
        echo "  restart - Restart both services"
        echo "  status  - Check service status"
        echo "  logs    - Show logs (optionally specify backend or frontend)"
        echo ""
        echo "Services:"
        echo "  Backend  - FastAPI + Stable Diffusion (port 8000)"
        echo "  Frontend - Rails UI (port 3000)"
        echo ""
        echo "Files:"
        echo "  Logs: $LOG_DIR/image_gen_*.log"
        echo "  PIDs: $LOG_DIR/image_gen_*.pid"
        exit 1
        ;;
esac
