# LogDrain - Architecture Design

## System Overview

LogDrain is a log aggregation service that captures logs from Railway-deployed applications through Railway's log drain feature, stores them in Loki, and provides visualization through Grafana dashboards.

```
Railway Services → Webhooks → Ingest Proxy → Loki ←→ Grafana
    ↑                                          ↓
    └───────────── API/Query ──────────────────┘
```

## Core Components

### 1. Ingest Proxy (Python/FastAPI)
- **Purpose**: Translate Railway log drain format → Loki push API
- **Location**: `/ingest/main.py`
- **Key Responsibilities**:
  - Receive HTTP POST from Railway webhooks
  - Parse NDJSON log lines
  - Transform to Loki format with labels
  - Push to Loki via HTTP API
  - Handle errors and retries
- **Technology**: Python 3.11+, FastAPI, httpx, pydantic
- **Port**: 8000
- **Health Check**: `/health`

### 2. Loki - Log Storage Engine
- **Purpose**: Specialized log storage and query engine
- **Location**: Ingest via HTTP API, Query via LogQL
- **Key Features**:
  - Label-based indexing
  - Fast querying for logs
  - Lightweight compared to Elasticsearch
  - Native integration with Grafana
- **Port**: 3100
- **Storage**: Filesystem (Railway persistent storage)
- **Retention**: 30 days default

### 3. Grafana - Visualization & Dashboard
- **Purpose**: Log visualization, querying, and dashboard UI
- **Location**: Web interface
- **Key Features**:
  - Dark theme
  - Service selector dropdown
  - Log level filter
  - Time range selector
  - Full-text search
  - Live tail mode
  - Log volume charts
- **Port**: 3000
- **Authentication**: Email + API key
- **Data Source**: Loki auto-configured

## Data Flow

### 1. Log Ingestion Flow
```
1. Railway Service emits log → Railway Log Drain
2. Railway sends HTTP POST → Ingest Proxy (webhook endpoint)
3. Ingest Proxy validates and parses NDJSON
4. Insert Proxy transforms to Loki format:
   {
     "streams": [
       {
         "stream": {
           "service": "provectusquantus",
           "deployment": "abc123",
           "environment": "production",
           "level": "INFO"
         },
         "values": [
           [timestamp_ns, message]
         ]
       }
     ]
   }
5. Ingest Proxy POST to Loki → Loki Push API
6. Loki stores with indexed labels
7. Grafana queries Loki → LogQL
8. User sees logs in Grafana dashboard
```

### 2. Log Format Mapping

**Railway NDJSON Entry:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "message": "Server started successfully",
  "level": "INFO",
  "service": "provectusquantus",
  "deploymentId": "dep_abc123",
  "environment": "production"
}
```

**Loki Entry:**
```json
{
  "streams": [
    {
      "stream": {
        "service": "provectusquantus",
        "level": "INFO"
      },
      "values": [
        ["1704100800000000000", "Server started successfully"]
      ]
    }
  ]
}
```

## Database Schema (Loki Streams)

### Primary Labels
- `service`: Service name (provectusquantus, projectboard)
- `environment`: Environment (production, staging)
- `level`: Log level (DEBUG, INFO, WARN, ERROR)
- `deployment_id`: Railway deployment ID

### Secondary Labels (Optional)
- `component`: Service component (api, worker, scheduler)
- `region`: Railway deployment region
- `build_id`: Build log identifier

### Indexing Strategy
- Service + level = primary index for filtering
- Deployment_id = correlation within specific deployment
- Timestamp = time-based queries
- Full-text search = regex on message content

## API Design

### Ingest Proxy Endpoints

#### `POST /api/v1/ingest/webhook`
**Railsay Log Drain Webhook**
- Auth: Railway webhook signature validation
- Body: NDJSON log lines
- Response: 200 OK on success, 500 on error
- Retry: Railway auto-retry on 5xx

#### `GET /health`
**Health Check**
- Response: 200 OK / {"status": "healthy"}
- Used by Railway health checks

### Authentication

#### Grafana Auth
- **A (CEO)**: Email login (alexlorenzo39@gmail.com), admin role
- **Claus**: API key for programmatic access
- **No Signup**: Disabled via config

#### Loki Auth
- No direct access (via Ingest Proxy and Grafana only)
- Internal API key for proxy → Loki communication

### LogQL Query Examples

#### Basic Queries
```logql
# All logs from provectusquantus
{service="provectusquantus"}

# ERROR logs in last 1 hour
{level="ERROR"} | line_format "{{ . }}" | json

# Search for "database" in messages
{service="projectboard"} |= "database"

# Build logs only
{service=~".+-build"}
```

#### Advanced Queries
```logql
# Rate of errors per service
sum(rate({level="ERROR", service=~".+"}[1m])) by (service)

# Top error messages
{level="ERROR"} | json | line_format "{{ .message }}" | topk(10, count)

# Correlation by deployment_id
{deployment_id="abc123"}
```

## Configuration

### Environment Variables
```bash
# Loki Configuration
LOKI_HOST=http://loki:3100
LOKI_PUSH_PATH=/loki/api/v1/push
INGEST_PORT=8000
INGEST_LOG_LEVEL=INFO

# Grafana Configuration
GF_SECURITY_ADMIN_EMAIL=alexlorenzo39@gmail.com
GF_SECURITY_ALLOW_EMBEDDING=true
GF_USERS_ALLOW_SIGN_UP=false
GF_AUTH_ANONYMOUS_ENABLED=false

# Railway-Specific
RAILWAY_WEBHOOK_SECRET=your_secret_here
ALLOWED_SERVICES=provectusquantus,projectboard
```

## Deployment

### Local Development
```bash
docker-compose up
grafana: http://localhost:3000
loki: http://localhost:3100
ingest: http://localhost:8000
```

### Railway Production
```bash
railway up --service=loki
railway up --service=grafana
railway up --service=ingest

# Configure log drains for each service to point to ingest webhook
```

## Security Considerations

1. **Ingest Proxy**
   - Validate Railway webhook signatures
   - Rate limiting on webhook endpoint
   - Sanitize log content to prevent injection
   - Internal-only access (no public ingress)

2. **Loki**
   - No direct public access
   - Authentication via API key from proxy/Grafana
   - Network policies to restrict access

3. **Grafana**
   - HTTPS only
   - Strong password for admin
   - No anonymous access
   - API key rotation

## Performance Considerations

1. **Loki Scaling**
   - Horizontal scaling via Loki distributed mode (future)
   - Retention policies to limit storage
   - WAL (Write-Ahead Log) for durability

2. **Ingest Proxy**
   - Async processing for high throughput
   - Connection pooling to Loki
   - Batching of log entries

3. **Grafana**
   - Query caching
   - Limited time ranges for large datasets
   - Auto-refresh optimization

## Monitoring & Observability

1. **Ingest Proxy Metrics**
   - Logs received count
   - Logs processed count
   - Processing time
   - Error rate

2. **Loki Metrics**
   - Storage usage
   - Query latency
   - Index size

3. **Grafana Metrics**
   - Dashboard views
   - Query performance
   - User activity

## Future Enhancements

1. **Alerting**: Log-based alerts (patterns, thresholds)
2. **Multi-Environment**: Support staging/dev environments
3. **Log Parsing**: Structured log parsing (JSON, structured logs)
4. **Archival**: Long-term archival to S3
5. **Analytics**: Log analytics and insights
