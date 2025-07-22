# 📝 Comprehensive Logging Guide

## Overview

This CodeSandbox application uses a comprehensive, industry-standard logging system that provides:

- **Structured JSON logging** for production
- **Colored console logging** for development  
- **Request correlation IDs** for tracing requests across services
- **Performance monitoring** with timing and slow request detection
- **Module-specific loggers** that can be enabled/disabled independently
- **Exception handling** with full stack traces
- **File rotation** to manage disk space
- **Environment-based configuration**

## Quick Start

### Basic Usage

```python
from app.utils.logger import Loggers

# Use pre-configured loggers
Loggers.api.info("Processing user request", user_id=123, action="create_workspace")
Loggers.services.warning("Database connection slow", duration_ms=1500)
Loggers.workspace_service.error("Workspace creation failed", exc=exception, workspace_data=data)
```

### With Context and Timing

```python
from app.utils.logger import Loggers, timed_operation, get_workspace_logger

# Time operations automatically
@timed_operation(Loggers.services, "database_query", threshold_ms=200)
async def get_user_workspaces(user_id: str):
    # Function automatically logged with timing
    return await db.query(...)

# Workspace-specific logging
workspace_logger = get_workspace_logger("ws-123")
workspace_logger.info("Creating new file", filename="example.py", size_bytes=1024)
```

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# === Logging Configuration ===
LOG_LEVEL=DEBUG                     # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_JSON_FORMAT=false              # true for JSON, false for colored console
LOG_FILE_ENABLED=true              # Enable log files  
LOG_MAX_FILE_SIZE_MB=10           # Max file size before rotation
LOG_BACKUP_COUNT=5                # Number of backup files to keep
LOG_PERFORMANCE_THRESHOLD_MS=1000  # Slow request warning threshold
```

### Development vs Production

- **Development**: Colorful console output with context
- **Production**: Structured JSON logs for parsing by log aggregation tools

The system auto-detects based on `ENVIRONMENT` setting.

## Available Loggers

### Pre-configured Logger Instances

```python
from app.utils.logger import Loggers

# Main application loggers
Loggers.app              # General application logs
Loggers.api              # API endpoint logs
Loggers.services         # Service layer logs
Loggers.middleware       # Middleware logs
Loggers.jupyter          # Jupyter server logs

# Service-specific loggers
Loggers.workspace_service    # Workspace operations
Loggers.execution_service    # Code execution
Loggers.file_service         # File operations

# API-specific loggers  
Loggers.api_routes          # Route handlers
Loggers.api_dependencies    # Dependencies
```

### Logger Hierarchy

```
app                          # Root application logger
├── app.api                 # API layer
│   ├── app.api.routes      # Route handlers
│   └── app.api.dependencies # Dependencies
├── app.services            # Service layer
│   ├── app.services.workspace
│   ├── app.services.execution  
│   └── app.services.file
├── app.middleware          # Middleware
├── app.jupyter             # Jupyter integration
├── app.access              # HTTP access logs
└── app.errors              # Error logs
```

## Logging Patterns

### 1. Basic Logging with Context

```python
from app.utils.logger import Loggers

def process_user_request(user_id: str, request_data: dict):
    Loggers.api.info("Processing user request",
                    user_id=user_id,
                    action=request_data.get("action"),
                    data_size=len(str(request_data)))
    
    try:
        result = perform_operation(request_data)
        Loggers.api.info("Request processed successfully",
                        user_id=user_id,
                        result_count=len(result))
        return result
    except Exception as e:
        Loggers.api.error("Request processing failed",
                         exc=e,
                         user_id=user_id,
                         request_data=request_data)
        raise
```

### 2. Performance Monitoring

```python
from app.utils.logger import timed_operation, Loggers

@timed_operation(Loggers.services, "expensive_calculation", threshold_ms=500)
async def expensive_calculation(data):
    # This function will be automatically timed
    # Logs warning if it takes longer than 500ms
    await asyncio.sleep(1)  # Simulated work
    return "result"

# Or use context manager for more control
from app.utils.logger import TimingLogger

timing_logger = TimingLogger(Loggers.services, threshold_ms=100)

async def process_data():
    with timing_logger.time_operation("data_processing", batch_size=1000):
        # Your operation here
        process_batch(data)
```

### 3. Exception Handling

```python
from app.utils.logger import log_exception, Loggers

@log_exception(Loggers.api, "Failed to create workspace")
async def create_workspace(workspace_data):
    # Exceptions are automatically logged with full context
    workspace = await workspace_service.create(workspace_data)
    return workspace

# Or manual exception logging
def risky_operation():
    try:
        dangerous_function()
    except Exception as e:
        Loggers.services.error("Operation failed with critical error",
                              exc=e,
                              operation="risky_operation",
                              context_data={"important": "info"})
        raise
```

### 4. Workspace-Specific Logging

```python
from app.utils.logger import get_workspace_logger

async def handle_workspace_operation(workspace_id: str):
    # Get logger bound to workspace
    ws_logger = get_workspace_logger(workspace_id)
    
    ws_logger.info("Starting workspace operation", operation="file_upload")
    
    try:
        result = await perform_workspace_task()
        ws_logger.info("Workspace operation completed", 
                      result_size=len(result),
                      files_processed=5)
    except Exception as e:
        ws_logger.error("Workspace operation failed", exc=e)
```

### 5. Function Call Tracing

```python
from app.utils.logger import log_function_call, Loggers

@log_function_call(Loggers.api_routes, include_args=True)
async def api_endpoint(user_id: str, workspace_data: dict):
    # Function entry/exit automatically logged
    # Arguments logged when include_args=True
    return await process_request(user_id, workspace_data)
```

## Log Output Examples

### Development Console Output

```
12:34:56 INFO            app.api | Processing user request [id=abc12345 ws=ws-789 user=user-123 took=45ms POST /workspaces → 201]
12:34:56 DEBUG           app.services.workspace | Creating workspace directory [id=abc12345 ws=ws-789 path=/tmp/workspaces/ws-789]  
12:34:57 WARNING         app.services | Slow operation: database_query [id=abc12345 took=1250ms threshold=1000ms slow_operation=true]
12:34:57 ERROR           app.errors | Database connection failed [id=abc12345 exception_type=ConnectionError exception_message="Connection refused"]
```

### Production JSON Output

```json
{"timestamp":"2024-01-15T12:34:56.789Z","level":"INFO","logger":"app.api","message":"Processing user request","correlation_id":"abc12345","workspace_id":"ws-789","user_id":"user-123","duration_ms":45,"http_method":"POST","http_path":"/workspaces","http_status":201}

{"timestamp":"2024-01-15T12:34:57.123Z","level":"ERROR","logger":"app.errors","message":"Database connection failed","correlation_id":"abc12345","exception":{"type":"ConnectionError","message":"Connection refused","traceback":"Traceback (most recent call last)..."}}
```

## Request Tracing

Every HTTP request gets a unique **correlation ID** that's automatically added to all logs within that request context.

### Correlation ID Features

- **Auto-generated** UUIDs for each request
- **Client-provided** via `X-Correlation-ID` header  
- **Response header** includes correlation ID
- **Automatic propagation** to all logs in request context

### Finding Related Logs

```bash
# Find all logs for a specific request
grep "abc12345" logs/app.log

# In production with JSON logs
jq 'select(.correlation_id == "abc12345")' logs/app.log
```

## Log Files and Rotation

### File Structure

```
logs/
├── app.log              # Main application logs
├── app.log.1           # Rotated backup
├── access.log          # HTTP access logs  
├── access.log.1        # Rotated backup
├── error.log           # Error-level logs only
└── error.log.1         # Rotated backup
```

### Rotation Settings

- **Max file size**: 10MB (configurable)
- **Backup files**: 5 (configurable)
- **Auto-rotation**: When size limit exceeded
- **Compression**: Available via external tools

## Performance Monitoring

### Automatic Timing

```python
# Logs execution time automatically
@timed_operation(Loggers.services, threshold_ms=200)
async def slow_function():
    await asyncio.sleep(0.5)  # Will log warning (500ms > 200ms threshold)
```

### Custom Metrics

```python
start_time = time.perf_counter()
# ... do work ...
duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

Loggers.api.info("Custom operation completed",
                operation="data_export", 
                duration_ms=duration_ms,
                records_processed=1000,
                bytes_written=51200)
```

## Debugging Tips

### 1. Enable Debug Logging

```bash
# In .env file
LOG_LEVEL=DEBUG
```

### 2. Module-Specific Debugging

```python
# Enable debug for specific modules
import logging
logging.getLogger("app.services").setLevel(logging.DEBUG)
logging.getLogger("app.jupyter").setLevel(logging.WARNING)  # Reduce noise
```

### 3. Correlation ID Tracking

Always include correlation ID when reporting issues:

```python
from app.middleware.logging_middleware import get_correlation_id

correlation_id = get_correlation_id()
print(f"Report this ID: {correlation_id}")
```

### 4. Log Analysis Commands  

```bash
# Recent errors
tail -f logs/error.log

# Slow requests
grep "slow_request.*true" logs/app.log

# Specific workspace activity
grep "workspace_id.*ws-123" logs/app.log
```

## Integration with Monitoring Tools

### ELK Stack (Elasticsearch, Logstash, Kibana)

```json
{
  "input": {
    "beats": {
      "port": 5044
    }
  },
  "filter": {
    "if": "[fields][service] == 'codesandbox'",
    "json": {
      "source": "message"
    }
  },
  "output": {
    "elasticsearch": {
      "hosts": ["localhost:9200"]
    }
  }
}
```

### Datadog Integration

```python
# Add to logging configuration
import logging
from datadog import DogStatsdClient

statsd = DogStatsdClient()

class DatadogHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            statsd.increment('codesandbox.errors', tags=[
                f'logger:{record.name}',
                f'level:{record.levelname}'
            ])
```

## Best Practices

### ✅ DO

- Use structured logging with key-value pairs
- Include relevant context in every log
- Use appropriate log levels
- Log both success and failure cases
- Include performance metrics
- Use correlation IDs for request tracing

### ❌ DON'T

- Log sensitive data (passwords, tokens, PII)
- Use string formatting in log messages
- Log in tight loops without rate limiting
- Mix print statements with proper logging
- Log at inappropriate levels (DEBUG in production)

## Troubleshooting

### Common Issues

#### 1. Logs Not Appearing

```python
# Check if logging is initialized
from app.core.logging_config import setup_logging
setup_logging()  # Call this early in your application
```

#### 2. Performance Impact

```python
# Use lazy evaluation for expensive operations
logger.debug("Processing data: %s", expensive_calculation if logger.isEnabledFor(logging.DEBUG) else "...")
```

#### 3. Log File Permissions

```bash
# Ensure write permissions
chmod 755 logs/
touch logs/app.log
chmod 644 logs/app.log
```

## Security Considerations

### PII Protection

```python
def sanitize_user_data(data):
    """Remove sensitive information before logging"""
    safe_data = data.copy()
    safe_data.pop('password', None)
    safe_data.pop('email', None)
    safe_data['user_id'] = safe_data.get('user_id', '')[:8] + '...'  # Partial ID
    return safe_data

Loggers.api.info("User data processed", user_data=sanitize_user_data(request_data))
```

### Token Masking

```python
def mask_token(token: str) -> str:
    """Mask sensitive tokens for logging"""
    if not token or len(token) < 8:
        return "[REDACTED]"
    return f"{token[:4]}...{token[-4:]}"

Loggers.jupyter.info("Jupyter server started", token=mask_token(settings.jupyter_token))
```

---

## Need Help?

- **Configuration issues**: Check environment variables and file permissions
- **Performance concerns**: Review log levels and file rotation settings  
- **Integration questions**: See monitoring tools section above
- **Custom requirements**: Extend the logger classes in `app/utils/logger.py`

The logging system is designed to be comprehensive yet easy to use. When in doubt, use structured logging with relevant context! 