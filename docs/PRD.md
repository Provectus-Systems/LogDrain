# LogDrain - Product Requirements Document

## Executive Summary
LogDrain is a centralized log aggregation service for Railway-deployed applications, providing real-time monitoring, debugging, and analysis capabilities through Grafana dashboards and Loki log storage.

## Problem Statement
- Railway CLI logs are unreliable and ephemeral
- No centralized view of logs across multiple services (ProvectusQuantus, ProjectBoard)
- Build logs are not captured or easily accessible
- Difficult to correlate issues across services
- No historical log retention or search capabilities

## Solution Overview
A lightweight log aggregation pipeline that captures both runtime and build logs from all Railway services, stores them in Loki, and provides intuitive visualization through Grafana dashboards.

## Requirements

### Functional Requirements
1. **Log Ingestion**
   - Accept log drains from multiple Railway services
   - Support both runtime logs and build logs
   - Handle NDJSON format from Railway webhooks
   - Minimal latency (ingest → queryable < 5 seconds)

2. **Log Storage & Query**
   - Store logs in Loki with proper labels (service, deployment, environment)
   - Support log retention policies (default: 30 days)
   - Efficient querying with LogQL
   - Handle at least 10,000 log lines per day

3. **Dashboard & Visualization**
   - Grafana dashboard with dark theme
   - Service selector dropdown with all Railway services
   - Log level filter (DEBUG, INFO, WARN, ERROR)
   - Time range selector
   - Full-text search bar
   - Live tail mode for real-time monitoring
   - Log volume charts by service/time

4. **Access Control**
   - A (CEO)登录 via Grafana console (alexlorenzo39@gmail.com) - read/write access
   - Claus (Lead Engineer) via API key - programmatic access
   - No public signup allowed
   - HTTPS only

5. **Deployment**
   - Host on Railway alongside existing services
   - Single docker-compose.yml for local development
   - Separate Dockerfiles for production deployment
   - Environment variable configuration

### Non-Functional Requirements
- **Reliability**: 99.9% uptime, handle ingest failures gracefully
- **Performance**: Query response time < 2 seconds for 24h data
- **Scalability**: Support up to 5 services, 50,000 logs/day
- **Security**: HTTPS, authentication, no log data exposure
- **Maintainability**: Minimal code, clear documentation, easy updates

## User Stories

### As A (CEO)
- I want to see all logs in one place to understand system health
- I want to filter by service to debug specific issues
- I want to search logs for specific errors or patterns
- I want to share log queries with Claus for collaboration

### As Claus (Lead Engineer)
- I want API access to query logs programmatically
- I want to set up alerts based on log patterns
- I want to export logs for detailed analysis
- I want live tail to monitor deployments in real-time

## Success Metrics
- All Railway services sending logs to LogDrain within 1 week
- Average query response time < 2 seconds
- Zero log loss during normal operations
- Both A and Claus using the dashboard weekly

## Out of Scope
- Log alerting (future phase)
- Log parsing/structuring beyond Railway format
- Multi-environment support (production only)
- Log archival to S3 (beyond 30 days)
- Advanced analytics or ML on logs

## Timeline
- Week 1: Infrastructure setup (Loki, Grafana, ingest proxy)
- Week 2: Dashboard creation and service integration
- Week 3: Testing, security hardening, documentation
- Week 4: Production deployment and monitoring

## Risks & Mitigation
1. **Risk**: Railway log drain format changes
   - **Mitigation**: Versioned ingest proxy, schema validation

2. **Risk**: Log volume exceeds Loki capacity
   - **Mitigation**: Monitoring, retention policies, scaling plan

3. **Risk**: Authentication issues block access
   - **Mitigation**: Admin bypass, backup API access

4. **Risk**: Network latency between Railway services
   - **Mitigation**: Host all services in same Railway region
