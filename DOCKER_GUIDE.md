# Docker Deployment Guide

## Overview

This project uses Docker and Docker Compose to containerize the entire BotSetu application including:
- **Frontend**: Next.js application (port 3000)
- **Backend**: Python scripts for Twilio integration
- **MongoDB**: Database (port 27017)

## Prerequisites

1. **Docker Desktop** installed
   - Windows: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Verify installation: `docker --version`

2. **Docker Compose** (included with Docker Desktop)
   - Verify: `docker-compose --version`

## Quick Start

### 1. Configure Environment Variables

Copy the example environment file:
```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your credentials:
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_actual_token
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
CLERK_SECRET_KEY=sk_test_xxxxx
MONGODB_URI=mongodb://mongodb:27017/
```

### 2. Build and Start Services

```powershell
# Build all containers
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **MongoDB**: mongodb://localhost:27017

## Service Details

### Frontend Container
- **Port**: 3000
- **Image**: Node.js 20 Alpine
- **Auto-restarts**: Yes
- **Health checks**: Enabled

### Backend Container
- **Image**: Python 3.11 Slim
- **Purpose**: Run Twilio scripts (creation.py, attach.py)
- **Interactive**: Yes (can execute scripts manually)

### MongoDB Container
- **Port**: 27017
- **Version**: 7.0
- **Persistent storage**: Docker volume
- **Database**: BotSetu

## Common Commands

### Start Services
```powershell
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d frontend
```

### Stop Services
```powershell
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### View Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f frontend
docker-compose logs -f backend
docker-compose logs -f mongodb
```

### Execute Commands in Containers

**Run Python scripts in backend:**
```powershell
# Access backend container
docker exec -it botsetu-backend bash

# Run creation script
python creation.py

# Run attach script
python attach.py
```

**Access MongoDB:**
```powershell
# MongoDB shell
docker exec -it botsetu-mongodb mongosh

# Use BotSetu database
use BotSetu

# View collections
show collections

# Query data
db['User-data'].find().pretty()
```

**Access Frontend container:**
```powershell
docker exec -it botsetu-frontend sh
```

### Rebuild Services

```powershell
# Rebuild all services
docker-compose build --no-cache

# Rebuild specific service
docker-compose build --no-cache frontend

# Rebuild and restart
docker-compose up -d --build
```

### Check Service Status
```powershell
# List running containers
docker-compose ps

# Check health status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Development Workflow

### Option 1: Docker for Everything
```powershell
# Start all services
docker-compose up -d

# Watch logs
docker-compose logs -f frontend

# Run backend scripts interactively
docker exec -it botsetu-backend python creation.py
```

### Option 2: Hybrid (MongoDB in Docker, Local Development)
```powershell
# Start only MongoDB
docker-compose up -d mongodb

# Run frontend locally
cd Frontend
npm run dev

# Run backend locally
cd Backend
python creation.py
```

## Volume Management

### View Volumes
```powershell
docker volume ls | Select-String "botsetu"
```

### Backup MongoDB Data
```powershell
# Create backup directory
New-Item -ItemType Directory -Force -Path ./backups

# Backup database
docker exec botsetu-mongodb mongodump --db=BotSetu --out=/dump
docker cp botsetu-mongodb:/dump ./backups/mongodb-backup-$(Get-Date -Format 'yyyy-MM-dd')
```

### Restore MongoDB Data
```powershell
# Copy backup to container
docker cp ./backups/mongodb-backup-2026-02-05 botsetu-mongodb:/restore

# Restore database
docker exec botsetu-mongodb mongorestore --db=BotSetu /restore/BotSetu
```

## Troubleshooting

### Container Won't Start
```powershell
# Check logs
docker-compose logs frontend

# Check if port is in use
netstat -ano | findstr :3000

# Restart specific service
docker-compose restart frontend
```

### MongoDB Connection Issues
```powershell
# Check MongoDB health
docker exec botsetu-mongodb mongosh --eval "db.adminCommand('ping')"

# Verify network
docker network inspect botsetu-network

# Check environment variables
docker exec botsetu-backend printenv | Select-String "MONGODB"
```

### Permission Issues
```powershell
# Fix volume permissions (Linux/Mac)
docker-compose down
docker volume rm botsetu_mongodb_data
docker-compose up -d
```

### Clear Everything and Start Fresh
```powershell
# Stop and remove containers, networks, volumes
docker-compose down -v

# Remove images
docker rmi botsetu-frontend botsetu-backend

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

## Production Deployment

### Security Checklist
- [ ] Use strong MongoDB passwords (update docker-compose.yml)
- [ ] Enable MongoDB authentication
- [ ] Use secrets management (Docker Swarm secrets or external vault)
- [ ] Enable HTTPS/SSL for frontend
- [ ] Restrict network exposure (use internal networks)
- [ ] Regular backups scheduled
- [ ] Update base images regularly
- [ ] Scan images for vulnerabilities

### Update docker-compose.yml for Production
```yaml
# Add MongoDB authentication
mongodb:
  environment:
    MONGO_INITDB_ROOT_USERNAME: admin
    MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}

# Use secrets for sensitive data
frontend:
  secrets:
    - clerk_secret
    
secrets:
  clerk_secret:
    external: true
```

### Deploy to Cloud
```powershell
# Build for production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Push to registry (Docker Hub, AWS ECR, etc.)
docker tag botsetu-frontend your-registry/botsetu-frontend:latest
docker push your-registry/botsetu-frontend:latest
```

## Performance Optimization

### Resource Limits
Add to docker-compose.yml:
```yaml
services:
  frontend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Health Checks
Already configured for frontend and MongoDB. Monitor with:
```powershell
docker inspect botsetu-frontend | Select-String -Pattern "Health"
```

## Useful Docker Commands

```powershell
# Remove unused images
docker image prune -a

# Remove stopped containers
docker container prune

# Remove unused volumes
docker volume prune

# View disk usage
docker system df

# Clean everything (use with caution)
docker system prune -a --volumes
```

## Next Steps

1. Configure your `.env` file with actual credentials
2. Run `docker-compose up -d`
3. Access http://localhost:3000
4. Create bots through the UI
5. Use backend container for Twilio operations

For detailed API integration, see **INTEGRATION_GUIDE.md** in the Backend folder.
