# Cloud Production Deployment Guide

Agent World cloud deployment configurations for AWS, GCP, Azure, and Docker.

## Quick Start (Docker Compose)

```bash
# 1. Copy environment template
cp .env.prod.example .env.prod

# 2. Edit with your values
nano .env.prod

# 3. Deploy
./scripts/deploy.sh docker .env.prod
```

## AWS Deployment

### Prerequisites
- AWS CLI configured
- Terraform installed
- Docker installed

### Steps

```bash
# 1. Build and push to ECR
cd aws
aws ecr get-login-password | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

docker build -t agent-world-backend ../backend
docker tag agent-world-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/agent-world-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/agent-world-backend:latest

# 2. Deploy infrastructure
cd aws
terraform init
terraform plan
terraform apply

# 3. Update ECS service
aws ecs update-service --cluster agent-world-prod --service agent-world-backend --force-new-deployment
```

### AWS Resources Created
- VPC with public/private subnets
- ECS Fargate cluster
- RDS PostgreSQL (Multi-AZ)
- ElastiCache Redis
- Application Load Balancer
- CloudWatch Logs
- Auto Scaling

## GCP Deployment

```bash
# Build and deploy to Cloud Run
gcloud run deploy agent-world \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production"
```

## Azure Deployment

```bash
# Build and push to ACR
az acr build --registry agentworld --image agent-world-backend ./backend

# Deploy to Container Instances
az container create \
  --resource-group agent-world \
  --name agent-world-backend \
  --image agentworld.azurecr.io/agent-world-backend:latest \
  --cpu 2 --memory 4 \
  --ports 8000
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Users     │────▶│    Nginx    │────▶│   Backend   │
└─────────────┘     │   (ALB)     │     │  (ECS/Fargate)
                    └─────────────┘     └──────┬──────┘
                           │                    │
                           ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   SSL/TLS   │     │   PostgreSQL │
                    │  (ACM/Let's │     │    (RDS)    │
                    │   Encrypt)  │     └─────────────┘
                    └─────────────┘            │
                                               ▼
                                        ┌─────────────┐
                                        │    Redis    │
                                        │ (ElastiCache)│
                                        └─────────────┘
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `JWT_SECRET` | Secret for JWT signing | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `WEBHOOK_SECRET` | Secret for webhook signing | Yes |
| `LOG_LEVEL` | Logging level (debug/info/warn) | No |

## Monitoring

### CloudWatch (AWS)
- CPU/Memory utilization
- Request count/latency
- Error rates
- Custom business metrics

### Grafana
- URL: http://localhost:3000 (docker) or ALB endpoint
- Default credentials: admin/admin

### Prometheus
- URL: http://localhost:9090
- Metrics endpoint: /metrics

## Backup & Recovery

### Database
- Automated daily backups (RDS)
- Point-in-time recovery (30 days)
- Cross-region backup replication

### Audit Logs
- S3 lifecycle policies
- Glacier transition after 90 days
- Immutable bucket option

## Security Checklist

- [ ] SSL certificates configured
- [ ] Database encryption enabled
- [ ] Secrets in Secrets Manager/Parameter Store
- [ ] Security groups configured
- [ ] WAF rules applied
- [ ] DDoS protection enabled
- [ ] VPC Flow Logs enabled
- [ ] CloudTrail enabled

## Scaling

### Horizontal Scaling
```bash
# AWS ECS
docker-compose -f docker-compose.prod.yml up -d --scale backend=5

# Or via ECS console
aws ecs update-service --cluster agent-world --service backend --desired-count 5
```

### Vertical Scaling
Edit task definition CPU/memory and redeploy.

## Troubleshooting

### View Logs
```bash
# Docker
docker-compose -f docker-compose.prod.yml logs -f backend

# AWS ECS
aws logs tail /ecs/agent-world-backend --follow
```

### Health Checks
```bash
curl http://localhost:8000/governance/v2/health/live
curl http://localhost:8000/governance/v2/health/ready
curl http://localhost:8000/governance/v2/health/deep
```

## Cost Optimization

- Use Fargate Spot for non-critical workloads
- Enable Reserved Instances for predictable workloads
- Set up billing alerts
- Review unused resources monthly

## Support

For deployment issues:
1. Check logs: `docker-compose logs` or CloudWatch
2. Verify environment variables
3. Check security group rules
4. Verify database connectivity
5. Check load balancer health checks
