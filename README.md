# LogDrain

Lightweight log aggregation service for Railway-deployed applications using Grafana + Loki.

## Overview

LogDrain captures runtime and build logs from all Railway services (ProvectusQuantus, ProjectBoard), stores them in Loki, and provides intuitive visualization through Grafana dashboards.

```
Railway Services → Log Drain → Ingest Proxy → Loki → Grafana
    ↓                                         ↑
    └────────────── API/Query ────────────────┘
```

## Features

- **Centralized Logging**: All Railway services logs in one place
- **Runtime & Build Logs**: Capture both types of logs
- **Grafana Dashboard**: Dark theme with intuitive filters
- **Service Filters**: Select specific services (ProvectusQuantus, ProjectBoard)
- **Log Level Filtering**: DEBUG, INFO, WARN, ERROR
- **Full-Text Search**: Search through log messages
- **Time Range Selection**: Custom time ranges
- **Live Tail**: Real-time log streaming
- **Volume Charts**: Visualize log volume by service and time
- **Secure Access**: Email + API key authentication

## Quick Start

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd LogDrain
```

2. Start services:
```bash
docker-compose up
```

3. Access services:
- Grafana: http://localhost:3000
  - Login: alexlorenzo39@gmail.com
  - Password: admin
- Loki: http://localhost:3100
- Ingest Proxy: http://localhost:8000

### Railway Production

1. Deploy to Railway:
```bash
railway login
railway up --service=loki
railway up --service=grafana
railway up --service=ingest
```

2. Configure log drains for your Railway services to point to:
```
https://<your-ingest-proxy-url>/api/v1/ingest/webhook
```

3. Add environment variables:
```bash
LOKI_HOST=http://loki:3100
GF_SECURITY_ADMIN_EMAIL=alexlorenzo39@gmail.com
GF_SECURITY_ALLOW_EMBEDDING=true
GF_USERS_ALLOW_SIGN_UP=false
GF_AUTH_ANONYMOUS_ENABLED=false
```

## Dashboard Features

### Service Selector
```markdown
Dropdown shows all configured services:
- ProvectusQuantus
- ProjectBoard
- ProvectusQuantus-build  (build logs)
- ProjectBoard-build      (build logs)
```

### Log Level Filter
- DEBUG: Development logs
- INFO: General information
- WARN: Warning messages
- ERROR: Error logs

### Search Bar
- Full-text search across log messages
- Regex search capabilities
- Case-sensitive/insensitive options

### Time Range
- Quick ranges: Last 5m, 15m, 1h, 6h, 24h, 7d, 30d
- Custom ranges
- Auto-refresh options

### Log Volume Charts
- Service-level volume over time
- Error rate charts
- Deployment correlation

## API Access

### Grafana API

1. Get API key from Grafana:
   - Go to Configuration → API Keys
   - Create new key with appropriate permissions

2. Query logs via API:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:3000/api/datasources/proxy/1/loki/api/v1/query_range?query={service=\"provectusquantus\"}&start=1704100800000000000&end=1704104400000000000"
```

### Ingest Proxy Webhook

```bash
curl -X POST http://localhost:8000/api/v1/ingest/webhook \
     -H "Content-Type: application/json" \
     -d '{"timestamp": "2024-01-01T12:00:00Z", "message": "Test log", "level": "INFO", "service": "test"}'
```

## LogQL Query Examples

```logql
# All logs from ProvectusQuantus
{service="provectusquantus"}

# ERROR logs only
{level="ERROR"}

# Search for "database" error
{service="projectboard"} |= "database"

# Last 1 hour of logs with rate limit
{service="provectusquantus"} limit 1000

# Error rate per minute
rate({level="ERROR"}[1m]) by (service)
```

## Configuration

### Environment Variables

```bash
# Loki Configuration
LOKI_HOST=http://loki:3100
LOKI_PUSH_PATH=/loki/api/v1/push
LOKI_RENTENTION_PERIOD=30d
LOKI_STORAGE_PATH=/loki

# Grafana Configuration
GF_SECURITY_ADMIN_EMAIL=alexlorenzo39@gmail.com
GF_SECURITY_ALLOW_EMBEDDING=true
GF_USERS_ALLOW_SIGN_UP=false
GF_AUTH_ANONYMOUS_ENABLED=false
GF_DEFAULT_THEME=dark
GF_LOG_LEVEL=info

# Ingest Proxy Configuration
INGEST_PORT=8000
INGEST_LOG_LEVEL=INFO
INGEST_MAX_RETRIES=3
INGEST_BATCH_SIZE=100

# Railway-Specific
RAILWAY_WEBHOOK_SECRET=your_secret_here
ALLOWED_SERVICES=provectusquantus,projectboard,provectusquantus-build,projectboard-build
```

### Docker Compose

```yaml
version: '3.8'
services:
  loki:
    image: grafana/loki:2.9.0
    ports: ["3100:3100"]
    command: -config.file=/etc/loki/local-config.yaml
    volumes: [./loki-config.yml:/etc/loki/local-config.yaml]

  grafana:
    image: grafana/grafana:10.1.0
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_SECURITY_ADMIN_EMAIL: alexlorenzo39@gmail.com
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards

  ingest:
    build: ./ingest
    ports: ["8000:8000"]
    depends_on: [loki]
    environment:
      LOKI_HOST: http://loki:3100
```

## Troubleshooting

### Ingest Proxy Not Receiving Logs

1. Check ingest proxy logs:
```bash
docker-compose logs ingest
```

2. Test webhook manually:
```bash
curl -X POST http://localhost:8000/api/v1/ingest/webhook \
     -H "Content-Type: application/json" \
     -d '{"test": "log"}'
```

3. Check Railway log drain configuration

### Loki Not Accepting Logs

1. Verify Loki is running:
```bash
curl http://localhost:3100/ready
```

2. Check Loki logs:
```bash
docker-compose logs loki
```

3. Test Loki push API:
```bash
curl -X POST http://localhost:3100/loki/api/v1/push \
     -H "Content-Type: application/json" \
     -d '{"streams": [{"stream": {"service": "test"}, "values": [["1704100800000000000", "test"]]}]}'
```

### Grafana Not Showing Logs

1. Verify datasource configuration
2. Check Grafana logs:
```bash
docker-compose logs grafana
```

3. Test datasource query:
```bash
curl "http://localhost:3000/api/datasources/proxy/1/loki/api/v1/labels"
```

## Development

### Local Development Setup

1. Create virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r ingest/requirements.txt
```

3. Run ingest proxy locally:
```bash
cd ingest
uvicorn main:app --reload --port 8000
```

4. Access: http://localhost:8000/docs (OpenAPI docs)

### Testing

```bash
# Run ingest tests
cd ingest
pytest tests/test_webhook.py

# Test Grafana dashboard
cd grafana/dashboards
./validate-dashboard.sh railway-logs.json
```

### Building

```bash
# Build all services
docker-compose build

# Build ingest proxy docker image only
cd ingest
docker build -t logdrain-ingest .
```

## Deployment

### Railway Deployment Guide

1. Create Railway project:
```bash
railway init
```

2. Add services:
```bash
railway add --name loki --image grafana/loki:2.9.0
railway add --name grafana --image grafana/grafana:10.1.0
railway add --name ingest --path ./ingest
```

3. Configure environment variables in Railway dashboard

4. Deploy:
```bash
railway deploy
```

5. Configure log drains for your services to point to the ingest webhook URL

### Production Considerations
- Set strong Grafana admin password
- Enable HTTPS via Railway custom domains
- Monitor Loki storage usage
- Set up Grafana API key rotation
- Configure log retention policies

## Architecture References

- [Architecture Documentation](./docs/ARCHITECTURE.md)
- [Product Requirements Document](./docs/PRD.md)

## Access Controls

- **A (CEO)**: alexlorenzo39@gmail.com - Grafana dashboard access, admin role
- **Claus**: API key - Programmatic access to Grafana/Loki APIs
- **Services**: Internal webhook endpoints only

## Monitoring

- Ingest Proxy logs: Check for webhook processing
- Loki logs: Check for storage and queries
- Grafana logs: Check for dashboard access
- Railway logs: Check for deployment health

## Performance

- Ingest Proxy: Handles 1000+ log lines/second
- Loki: Designed for log storage, efficient queries
- Grafana: Optimized dashboard for log exploration
- Average query latency: < 2 seconds for 24h data

## Troubleshooting Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- Railway Webhook Documentation

## Contributing

This is an internal project for Provects Systems.

## License

Private to Provects Systems.
