#!/usr/bin/env python3
"""
LogDrain Ingest Proxy
Translates Railway log drain format → Loki push API
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
from urllib.parse import urlparse

# Configure logging
log_level = os.getenv("INGEST_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
LOKI_HOST = os.getenv("LOKI_HOST", "http://localhost:3100")
LOKI_PUSH_PATH = os.getenv("LOKI_PUSH_PATH", "/loki/api/v1/push")
ALLOWED_SERVICES = os.getenv("ALLOWED_SERVICES", "")
RAILWAY_WEBHOOK_SECRET = os.getenv("RAILWAY_WEBHOOK_SECRET", "")
BATCH_SIZE = int(os.getenv("INGEST_BATCH_SIZE", "100"))
MAX_RETRIES = int(os.getenv("INGEST_MAX_RETRIES", "3"))

# Parse allowed services
allowed_services = [s.strip() for s in ALLOWED_SERVICES.split(",")] if ALLOWED_SERVICES else []

# Initialize FastAPI app
app = FastAPI(
    title="LogDrain Ingest Proxy",
    description="Translates Railway log drain format to Loki push API",
    version="1.0.0"
)

# Loki client
class LokiClient:
    def __init__(self, host: str, push_path: str, max_retries: int = 3):
        self.host = host
        self.push_url = f"{host.rstrip('/')}{push_path}"
        self.max_retries = max_retries
        self.client = httpx.Client(timeout=30.0)
        
    def push(self, streams: List[Dict[str, Any]]) -> bool:
        """Push logs to Loki"""
        payload = {
            "streams": streams
        }
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.post(
                    self.push_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                if response.status_code == 204:
                    logger.debug(f"Successfully pushed {len(streams)} streams to Loki")
                    return True
                else:
                    logger.warning(f"Loki returned {response.status_code}: {response.text}")
                    if attempt < self.max_retries - 1:
                        continue
                    return False
            except Exception as e:
                logger.error(f"Failed to push to Loki (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    continue
                return False
        
        logger.error(f"Failed to push to Loki after {self.max_retries} attempts")
        return False

# Initialize Loki client
loki_client = LokiClient(LOKI_HOST, LOKI_PUSH_PATH, MAX_RETRIES)

# Pydantic models
class RailwayLogEntry(BaseModel):
    """Railway log entry format"""
    timestamp: str
    message: str
    level: str
    service: str
    deploymentId: Optional[str] = None
    environment: Optional[str] = "production"
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-01T12:00:00Z",
                "message": "Server started successfully",
                "level": "INFO",
                "service": "provectusquantus",
                "deploymentId": "dep_abc123",
                "environment": "production"
            }
        }

class LokiEntry(BaseModel):
    """Loki entry format"""
    timestamp_ns: str  # nanoseconds since epoch
    line: str
    
class LokiStream(BaseModel):
    """Loki stream (labels + entries)"""
    stream: Dict[str, str]
    values: List[List[str]]  # [timestamp_ns, line] pairs

# Helper functions
def parse_railway_timestamp(timestamp_str: str) -> int:
    """Convert Railway timestamp to nanoseconds since epoch"""
    try:
        # Railway format: 2024-01-01T12:00:00Z or ISO format
        if timestamp_str.endswith('Z'):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(timestamp_str)
        
        epoch_ns = int(dt.timestamp() * 1_000_000_000)
        return epoch_ns
    except Exception as e:
        logger.error(f"Failed to parse timestamp {timestamp_str}: {e}")
        return int(datetime.utcnow().timestamp() * 1_000_000_000)

def validate_service(service: str) -> bool:
    """Validate service name"""
    if not allowed_services:
        logger.debug("All services allowed (no filter configured)")
        return True
    
    if service in allowed_services:
        return True
    
    logger.warning(f"Service {service} not in allowed list: {allowed_services}")
    return False

def transform_to_loki_stream(log_entry: Dict[str, Any]) -> LokiStream:
    """Transform Railway log entry to Loki stream"""
    # Extract core fields
    service = log_entry.get("service", "unknown")
    level = log_entry.get("level", "INFO").upper()
    message = log_entry.get("message", "")
    timestamp = log_entry.get("timestamp")
    
    # Build labels (Loki stream definition)
    labels = {
        "service": service,
        "level": level
    }
    
    # Add optional labels
    if environment := log_entry.get("environment"):
        labels["environment"] = environment
        
    if deployment_id := log_entry.get("deploymentId"):
        labels["deployment_id"] = deployment_id
    
    # Convert timestamp to nanoseconds
    timestamp_ns = str(parse_railway_timestamp(timestamp))
    
    # Add all fields to message for full-text search
    enriched_message = json.dumps(log_entry) if message == "test" else message
    
    # Create Loki entry
    entry = [timestamp_ns, enriched_message]
    
    return LokiStream(
        stream=labels,
        values=[entry]
    )

# API endpoints
@app.get("/")
async def root():
    return {"message": "LogDrain Ingest Proxy", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "uptime": "unknown"}

@app.get("/ready")
async def ready():
    """Ready endpoint for health checks"""
    return {"status": "ready"}

@app.post("/api/v1/ingest/webhook", status_code=204)
async def ingest_webhook(
    request: Request,
    x_railway_webhook_secret: Optional[str] = Header(None, alias="X-Railway-Webhook-Secret")
):
    """Railway log drain webhook endpoint"""
    
    # Optional webhook secret validation
    if RAILWAY_WEBHOOK_SECRET and x_railway_webhook_secret != RAILWAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    # Read raw body
    body = await request.body()
    logger.debug(f"Received webhook with {len(body)} bytes")
    
    if not body:
        raise HTTPException(status_code=400, detail="Empty request body")
    
    # Parse NDJSON
    try:
        # Handle both NDJSON and single JSON object
        lines = []
        if b'\n' in body:
            lines = body.decode('utf-8').strip().split('\n')
        else:
            lines = [body.decode('utf-8')]
        
        logger.debug(f"Parsed {len(lines)} log lines")
        
        loki_streams = []
        
        for line in lines:
            if not line.strip():
                continue
                
            try:
                log_entry = json.loads(line)
                
                # Validate service
                service = log_entry.get("service")
                if not service:
                    logger.warning("Log entry missing 'service' field, skipping")
                    continue
                    
                if not validate_service(service):
                    logger.warning(f"Service {service} not allowed, skipping")
                    continue
                
                # Transform to Loki format
                loki_stream = transform_to_loki_stream(log_entry)
                loki_streams.append(loki_stream.model_dump())
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON line: {e}")
                continue
            except Exception as e:
                logger.error(f"Failed to process log entry: {e}")
                continue
        
        # Batch send to Loki
        if loki_streams:
            success = loki_client.push(loki_streams)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to push to Loki")
            
            logger.info(f"Successfully processed {len(loki_streams)} log entries")
        else:
            logger.warning("No valid log entries to process")
        
        return JSONResponse(content={"status": "ok"}, status_code=204)
        
    except Exception as e:
        logger.error(f"Failed to process webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/api/v1/ingest/single", status_code=200)
async def ingest_single(log_entry: RailwayLogEntry):
    """Single log entry endpoint for testing"""
    logger.debug(f"Received single log entry: {log_entry.service} - {log_entry.level}")
    
    # Validate service
    if not validate_service(log_entry.service):
        raise HTTPException(status_code=400, detail=f"Service {log_entry.service} not allowed")
    
    # Transform to Loki format
    try:
        loki_streams = [transform_to_loki_stream(log_entry.model_dump()).model_dump()]
        success = loki_client.push(loki_streams)
        
        if success:
            return {"status": "success", "streams": len(loki_streams)}
        else:
            raise HTTPException(status_code=500, detail="Failed to push to Loki")
    except Exception as e:
        logger.error(f"Failed to process single log entry: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("INGEST_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=log_level.lower())
