# Retry Configuration System - Documentation

## Overview

The Construction Cost Estimator now includes **robust retry logic with exponential backoff** to handle:

- API rate limits and timeouts
- Network connectivity issues
- File system errors
- Transient failures

## Features Implemented

### ✅ **1. Exponential Backoff**

- Progressively increasing delays between retries
- Prevents overwhelming services with rapid retry attempts
- Configurable base delay and maximum delay

### ✅ **2. Configurable Retry Attempts**

- Default: 5 attempts for API calls
- Default: 3 attempts for file operations
- Customizable per operation type

### ✅ **3. Timeout Handling**

- Maximum total time limits for operations
- Default: 5 minutes for API calls
- Default: 30 seconds for file operations
- Prevents indefinite hangs

### ✅ **4. Graceful Error Messages**

- User-friendly error messages
- Technical details logged for debugging
- Clear guidance on next steps

## Configuration Profiles

### API Retry Config

```python
API_RETRY_CONFIG = RetryConfig(
    max_attempts=5,        # Up to 5 retry attempts
    initial_delay=1.0,     # Start with 1 second delay
    max_delay=30.0,        # Max 30 seconds between retries
    exponential_base=2.0,  # Double delay each retry
    timeout=300.0,         # Total timeout: 5 minutes
)
```

**Retry Schedule:**

- Attempt 1: Immediate
- Attempt 2: After 1 second
- Attempt 3: After 2 seconds
- Attempt 4: After 4 seconds
- Attempt 5: After 8 seconds

### File Operations Config

```python
FILE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=0.5,
    max_delay=5.0,
    timeout=30.0,
)
```

### Network Operations Config

```python
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    initial_delay=2.0,
    max_delay=60.0,
    timeout=180.0,
)
```

## Usage Examples

### Basic Usage with Decorator

```python
from utils.retry_config import with_retry, API_RETRY_CONFIG

@with_retry(API_RETRY_CONFIG)
def call_gemini_api():
    # Your API call here
    response = agent.generate(prompt)
    return response
```

### Async Functions

```python
from utils.retry_config import with_async_retry

@with_async_retry()
async def async_api_call():
    response = await agent.generate_async(prompt)
    return response
```

### Custom Configuration

```python
from utils.retry_config import RetryConfig, with_retry

custom_config = RetryConfig(
    max_attempts=10,
    initial_delay=0.5,
    max_delay=120.0,
    timeout=600.0
)

@with_retry(custom_config)
def my_critical_operation():
    # Operation that needs more retries
    pass
```

## Where Retry Logic is Applied

### 1. **File Writer Tool** (`tools/file_writer_tool.py`)

- Automatic retries for file write operations
- Handles permission errors, disk full, etc.
- Returns graceful errors on final failure

```python
@with_retry(FILE_RETRY_CONFIG)
def write_estimate_report(html_content, estimate_data):
    # File operations with automatic retry
    Path(filename).write_text(content)
```

### 2. **Agent Runner** (`agent_runner.py`)

- Error handling for agent interactions
- Graceful error messages for users
- Automatic retry suggestions

```python
try:
    events = runner.run_async(...)
except Exception as e:
    error_msg = get_user_friendly_error(e)
    print(f"❌ Error: {error_msg}")
```

### 3. **API Server** (`api_server.py`)

- REST endpoint with retry logic
- HTTP error codes for different failures
- Structured error responses

```python
@app.route('/api/estimate', methods=['POST'])
@with_retry(API_RETRY_CONFIG)
def get_estimate():
    # API endpoint with automatic retry
    pass
```

## Error Messages

### User-Friendly Messages

The system converts technical errors into helpful messages:

| Technical Error       | User Message                                                               |
| --------------------- | -------------------------------------------------------------------------- |
| `ConnectionError`     | "Unable to connect to the service. Please check your internet connection." |
| `TimeoutError`        | "The request took too long to complete. Please try again."                 |
| `PermissionError`     | "Permission denied. Please check file permissions."                        |
| `RetryExhaustedError` | "The operation failed after multiple attempts. Please try again later."    |

### Technical Details

For debugging, technical details are logged:

```
[2025-11-19 10:30:15] WARNING: Operation 'write_estimate_report' failed on attempt 2/3:
  PermissionError: [Errno 13] Permission denied: 'output/estimate.html'
[2025-11-19 10:30:16] INFO: Retrying in 1.00 seconds...
```

## Monitoring and Logging

### Log Levels

- `INFO`: Successful retries, operation status
- `WARNING`: Failed attempts (before final failure)
- `ERROR`: Final failures, non-retryable errors

### Example Logs

```
INFO: Operation 'write_estimate_report' succeeded on attempt 2
WARNING: Operation 'call_api' failed on attempt 3/5: ConnectionError
ERROR: Operation 'save_file' failed after 3 attempts
```

## Testing Retry Logic

Run the demo script to see retry behavior:

```bash
python utils/retry_config.py
```

This will:

- Simulate failures with various retry scenarios
- Show exponential backoff in action
- Demonstrate graceful error handling

## Production Recommendations

### 1. **Monitor Retry Rates**

Track how often retries occur:

```python
# Add metrics tracking
retry_count = 0
success_after_retry = 0
```

### 2. **Adjust Configs Based on Environment**

```python
if os.getenv('ENVIRONMENT') == 'production':
    API_RETRY_CONFIG.max_attempts = 3  # Fewer retries in prod
else:
    API_RETRY_CONFIG.max_attempts = 5  # More retries in dev
```

### 3. **Circuit Breaker Pattern**

For repeated failures, implement circuit breaker:

```python
if consecutive_failures > 10:
    # Stop trying, alert ops team
    send_alert("API consistently failing")
```

### 4. **Rate Limiting Awareness**

Respect API rate limits:

```python
# Add rate limiting between requests
time.sleep(rate_limit_delay)
```

## API Server Endpoints

### Health Check

```bash
curl http://localhost:5000/api/health
```

Response:

```json
{
  "status": "healthy",
  "service": "Construction Cost Estimator API",
  "version": "1.0.0"
}
```

### Get Estimate (with retry)

```bash
curl -X POST http://localhost:5000/api/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Build a 3-bedroom house in Nairobi",
    "session_id": "session-123"
  }'
```

Response:

```json
{
  "success": true,
  "response": "Cost estimate HTML...",
  "session_id": "session-123",
  "metadata": {
    "model": "gemini-2.0-flash-001",
    "timestamp": "2025-11-19T10:30:00"
  }
}
```

Error Response:

```json
{
  "success": false,
  "error": "Unable to connect to the service. Please check your internet connection.",
  "technical_error": "ConnectionError: Max retries exceeded"
}
```

## Configuration Files

### Environment Variables (.env)

```bash
GOOGLE_API_KEY=your_api_key_here
PORT=5000
DEBUG=False
ENVIRONMENT=production
```

### Retry Settings

Edit `utils/retry_config.py` to customize:

- Retry attempts
- Backoff multipliers
- Timeout values
- Retryable exception types

## Troubleshooting

### Issue: Too Many Retries

**Solution:** Reduce `max_attempts` or increase `initial_delay`

### Issue: Timeout Too Short

**Solution:** Increase `timeout` value in config

### Issue: Not Retrying Expected Errors

**Solution:** Add error type to `retryable_exceptions` tuple

### Issue: Excessive Logging

**Solution:** Adjust logging level:

```python
logging.basicConfig(level=logging.WARNING)  # Only show warnings and errors
```

## Summary

Your Construction Cost Estimator now has:

- ✅ **5 retry attempts** for API calls with exponential backoff
- ✅ **3 retry attempts** for file operations
- ✅ **5-minute timeout** for API operations
- ✅ **Graceful error messages** for end users
- ✅ **Detailed logging** for debugging
- ✅ **REST API** with built-in retry logic

The system is now **production-ready** with robust error handling! 🚀
