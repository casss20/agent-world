#!/bin/bash
# Production Deployment Script for Agent World
# Usage: ./deploy.sh [aws|gcp|azure|docker]

set -e

PLATFORM=${1:-docker}
ENV_FILE=${2:-.env.prod}

echo "=== Agent World Production Deployment ==="
echo "Platform: $PLATFORM"
echo "Environment: $ENV_FILE"
echo ""

# Check environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Environment file $ENV_FILE not found!"
    echo "   Copy .env.prod.example to $ENV_FILE and fill in values."
    exit 1
fi

# Load environment variables
export $(grep -v '^#' $ENV_FILE | xargs)

echo "Step 1: Pre-deployment checks..."

# Check required variables
if [ -z "$JWT_SECRET" ] || [ "$JWT_SECRET" = "change_me_to_random_64_char_string" ]; then
    echo "❌ Error: JWT_SECRET not set!"
    exit 1
fi

if [ -z "$DB_PASSWORD" ] || [ "$DB_PASSWORD" = "change_me_to_strong_password_32_chars" ]; then
    echo "❌ Error: DB_PASSWORD not set!"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-..." ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set - some features will be disabled"
fi

echo "✅ Environment variables validated"

# Platform-specific deployment
case $PLATFORM in
    docker)
        echo ""
        echo "Step 2: Docker deployment..."
        
        # Pull latest images
        docker-compose -f docker-compose.prod.yml pull
        
        # Build backend
        docker-compose -f docker-compose.prod.yml build backend chatdev
        
        # Start services
        docker-compose -f docker-compose.prod.yml up -d
        
        # Wait for database
        echo "Waiting for database..."
        sleep 10
        
        # Run migrations
        echo "Running database migrations..."
        docker-compose -f docker-compose.prod.yml exec -T backend \
            python -c "from governance_v2.audit_service import get_audit_service; import asyncio; asyncio.run(get_audit_service().initialize())"
        
        echo "✅ Docker deployment complete!"
        echo ""
        echo "Services:"
        echo "  - API: http://localhost:8000"
        echo "  - Grafana: http://localhost:3000"
        echo "  - Prometheus: http://localhost:9090"
        ;;
    
    aws)
        echo ""
        echo "Step 2: AWS deployment..."
        
        # Check AWS CLI
        if ! command -v aws &> /dev/null; then
            echo "❌ AWS CLI not installed"
            exit 1
        fi
        
        # Deploy to ECS
        echo "Deploying to ECS..."
        aws ecs update-service \
            --cluster agent-world-prod \
            --service agent-world-backend \
            --force-new-deployment
        
        echo "✅ AWS deployment complete!"
        ;;
    
    gcp)
        echo ""
        echo "Step 2: GCP deployment..."
        
        # Check gcloud
        if ! command -v gcloud &> /dev/null; then
            echo "❌ gcloud not installed"
            exit 1
        fi
        
        # Deploy to Cloud Run
        echo "Deploying to Cloud Run..."
        gcloud run deploy agent-world \
            --source . \
            --platform managed \
            --region us-central1 \
            --allow-unauthenticated
        
        echo "✅ GCP deployment complete!"
        ;;
    
    azure)
        echo ""
        echo "Step 2: Azure deployment..."
        
        # Check Azure CLI
        if ! command -v az &> /dev/null; then
            echo "❌ Azure CLI not installed"
            exit 1
        fi
        
        echo "✅ Azure deployment not yet implemented"
        ;;
    
    *)
        echo "❌ Unknown platform: $PLATFORM"
        echo "Usage: ./deploy.sh [docker|aws|gcp|azure] [env-file]"
        exit 1
        ;;
esac

# Health check
echo ""
echo "Step 3: Health checks..."
sleep 5

if curl -sf http://localhost:8000/governance/v2/health/live > /dev/null; then
    echo "✅ Backend health check passed"
else
    echo "⚠️  Backend health check failed - check logs: docker-compose -f docker-compose.prod.yml logs backend"
fi

# Summary
echo ""
echo "=== Deployment Summary ==="
echo "Platform: $PLATFORM"
echo "Status: $(if curl -sf http://localhost:8000/governance/v2/health/live > /dev/null; then echo '✅ Healthy'; else echo '⚠️  Check logs'; fi)"
echo ""
echo "Next steps:"
echo "  1. Configure SSL certificates"
echo "  2. Set up DNS records"
echo "  3. Configure monitoring alerts"
echo "  4. Test end-to-end workflows"
echo ""
echo "Commands:"
echo "  View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "  Scale: docker-compose -f docker-compose.prod.yml up -d --scale backend=3"
echo "  Stop: docker-compose -f docker-compose.prod.yml down"
