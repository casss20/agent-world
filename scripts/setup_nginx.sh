#!/bin/bash
# Nginx Setup Script for Agent World
# Phase 3: Nginx reverse proxy deployment

set -e

echo "=== Agent World Nginx Setup ==="
echo ""

# Configuration
DOMAIN=${DOMAIN:-"api.agent-world.com"}
EMAIL=${EMAIL:-"admin@agent-world.com"}
BACKEND_PORT=${BACKEND_PORT:-8000}
NGINX_DIR="/root/.openclaw/workspace/agent-world/nginx"

echo "Domain: $DOMAIN"
echo "Backend Port: $BACKEND_PORT"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Warning: Not running as root. Some operations may fail."
    echo "   Consider running with sudo for production deployment."
    echo ""
fi

# Install Nginx if not present
echo "Step 1: Checking Nginx installation..."
if ! command -v nginx &> /dev/null; then
    echo "Installing Nginx..."
    apt-get update
    apt-get install -y nginx
else
    echo "✓ Nginx already installed"
fi

# Create SSL directory
echo ""
echo "Step 2: Setting up SSL certificates..."
mkdir -p /etc/nginx/ssl

# Check for existing certificates
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "✓ Let's Encrypt certificates found"
    # Create symlinks
    ln -sf "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" /etc/nginx/ssl/cert.pem
    ln -sf "/etc/letsencrypt/live/$DOMAIN/privkey.pem" /etc/nginx/ssl/key.pem
elif [ -f "$NGINX_DIR/ssl/cert.pem" ]; then
    echo "✓ Custom certificates found in nginx/ssl/"
    cp "$NGINX_DIR/ssl/cert.pem" /etc/nginx/ssl/cert.pem
    cp "$NGINX_DIR/ssl/key.pem" /etc/nginx/ssl/key.pem
    chmod 600 /etc/nginx/ssl/key.pem
else
    echo "⚠️  No SSL certificates found!"
    echo "   Generating self-signed certificate for testing..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/key.pem \
        -out /etc/nginx/ssl/cert.pem \
        -subj "/CN=$DOMAIN"
    echo "   ⚠️  WARNING: Using self-signed certificate!"
    echo "   For production, use Let's Encrypt or a valid certificate."
fi

# Backup original nginx config
echo ""
echo "Step 3: Backing up original configuration..."
if [ -f "/etc/nginx/nginx.conf" ]; then
    cp /etc/nginx/nginx.conf "/etc/nginx/nginx.conf.backup.$(date +%Y%m%d%H%M%S)"
    echo "✓ Original config backed up"
fi

# Copy new configuration
echo ""
echo "Step 4: Installing Agent World configuration..."
cp "$NGINX_DIR/nginx.conf" /etc/nginx/nginx.conf

# Update domain in config
sed -i "s/api.agent-world.com/$DOMAIN/g" /etc/nginx/nginx.conf

# Test configuration
echo ""
echo "Step 5: Testing Nginx configuration..."
nginx -t

# Create log directory
echo ""
echo "Step 6: Setting up log directory..."
mkdir -p /var/log/nginx
chown www-data:www-data /var/log/nginx

# Setup log rotation
echo ""
echo "Step 7: Configuring log rotation..."
cat > /etc/logrotate.d/agent-world-nginx << 'EOF'
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
EOF

echo "✓ Log rotation configured"

# Start/restart Nginx
echo ""
echo "Step 8: Starting Nginx..."
if systemctl is-active --quiet nginx; then
    systemctl reload nginx
    echo "✓ Nginx reloaded"
else
    systemctl start nginx
    systemctl enable nginx
    echo "✓ Nginx started and enabled"
fi

# Check backend availability
echo ""
echo "Step 9: Checking backend availability..."
if curl -s "http://localhost:$BACKEND_PORT/governance/v2/health/live" > /dev/null; then
    echo "✓ Backend is responding on port $BACKEND_PORT"
else
    echo "⚠️  Backend not responding on port $BACKEND_PORT"
    echo "   Make sure the FastAPI server is running:"
    echo "   cd ~/.openclaw/workspace/agent-world/backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000"
fi

# Test Nginx endpoints
echo ""
echo "Step 10: Testing Nginx endpoints..."
sleep 2

if curl -s -o /dev/null -w "%{http_code}" "http://localhost/governance/v2/health/live" | grep -q "200\|301\|302"; then
    echo "✓ Nginx health endpoint responding"
else
    echo "⚠️  Health endpoint not responding (may need backend)"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Configuration Summary:"
echo "  Domain: $DOMAIN"
echo "  Nginx Config: /etc/nginx/nginx.conf"
echo "  SSL Certs: /etc/nginx/ssl/"
echo "  Logs: /var/log/nginx/"
echo ""
echo "Test Commands:"
echo "  curl http://localhost/governance/v2/health/live"
echo "  curl -k https://localhost/governance/v2/health/live"
echo ""
echo "Next Steps:"
echo "  1. Obtain SSL certificate (Let's Encrypt recommended)"
echo "  2. Update DNS to point to this server"
echo "  3. Configure firewall (allow 80, 443)"
echo "  4. Monitor logs: tail -f /var/log/nginx/access.log"
echo ""

# SSL certificate helper
echo "=== SSL Certificate Helper ==="
echo ""
echo "For Let's Encrypt (production):"
echo "  certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive"
echo ""
echo "For self-signed (testing only):"
echo "  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\"
echo "    -keyout /etc/nginx/ssl/key.pem \\"
echo "    -out /etc/nginx/ssl/cert.pem \\"
echo "    -subj \"/CN=$DOMAIN\""
echo ""
