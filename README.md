# Datadog MCP Server

This [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
server that provides Datadog integration for Claude Code and other MCP
clients.  The focus is on Case Management, Events and Logging
capabilities.

The official [Datadog MCP Server](https://www.datadoghq.com/blog/datadog-remote-mcp-server/)
implements very limited subset of tools that I use.

Also, for some reason for Case Management Datadog keeps some API endpoints
undocumented:

- Link cases
- Get case comments (creating and deleting comments are public APIs,
  but retrieving comments is not, sic!)

## Features

- **No external dependencies** - Uses only Python standard library
- **Simple setup** - Configure with environment variables
- **MCP compliant** - Works with Claude Code and other MCP clients
- **Direct CLI usage** - Can be used standalone or as an MCP server

## Tools

### `datadog_search_cases`
Search Datadog cases with server-side filtering.

**Parameters:**
- `filter` (string, optional): Search query supporting free text and field prefixes
  - Examples: `"circuit breaker"`, `"status:open"`, `"circuit breaker mapping-pipeline status:open"`
  - Status prefixes: `status:open`, `status:in_progress`, `status:closed`
- `page_size` (integer, optional): Cases per page (default: 100, max: 100)
- `page_number` (integer, optional): Page number, 1-based (default: 1)
- `sort_field` (string, optional): Sort field - `"created_at"`, `"priority"`, or `"status"` (default: `"created_at"`)
- `sort_asc` (boolean, optional): Sort ascending (default: false = newest first)

**Example:**
```python
# Search for open circuit breaker cases
datadog_search_cases(
    filter="circuit breaker status:open",
    page_size=50
)

# Get all in-progress cases
datadog_search_cases(filter="status:in_progress")
```

### `datadog_get_case`
Retrieve detailed information about a Datadog case by its key.

**Parameters:**
- `key` (string): Case key, e.g., `"KEY-718"`

**Example:**
```python
datadog_get_case(key="KEY-718")
```

### `datadog_comment_case`
Add a comment to a Datadog case.

**Parameters:**
- `key` (string): Case key, e.g., `"KEY-718"`
- `comment` (string): Comment text to add to the case

**Example:**
```python
datadog_comment_case(
    key="KEY-718",
    comment="This is a test comment"
)
```

### `datadog_set_case_status`
Set the status of a Datadog case.

**Parameters:**
- `key` (string): Case key, e.g., `"KEY-718"`
- `status` (string): Case status - must be one of:
  - `"IN_PROGRESS"` - Case is being worked on
  - `"OPEN"` - Case is open and awaiting action
  - `"CLOSED"` - Case is closed

**Example:**
```python
datadog_set_case_status(key="KEY-718", status="IN_PROGRESS")
```

### `datadog_link_cases`
Create a relationship between two Datadog cases.

**Parameters:**
- `parent_key` (string): Parent case key, e.g., `"KEY-718"`
- `child_key` (string): Child case key, e.g., `"KEY-792"`
- `relationship` (string): Relationship type (default: `"DUPLICATES"`)
  - Valid values: `"DUPLICATES"`, `"RELATES_TO"`, `"BLOCKS"`

**Example:**
```python
datadog_link_cases(parent_key="KEY-718", child_key="KEY-792", relationship="DUPLICATES")
```

### `datadog_logs_search`
Search Datadog logs with a query string.

**Parameters:**
- `query` (string): Log search query
  - Examples: `"job_id:abc-123"`, `"service:my-service status:error"`, `"*"` (all logs)
  - Supports attribute searches: `"@http.status_code:500"`
- `time_range` (string, optional): Time range for search (default: `"1h"`)
  - Examples: `"1h"` (last hour), `"1d"` (last day), `"7d"` (last 7 days), `"30m"` (last 30 minutes)
- `limit` (integer, optional): Maximum number of logs to return (default: 100, max: 1000)
- `sort` (string, optional): Sort order (default: `"-timestamp"` for newest first)
  - `"-timestamp"`: Newest first
  - `"timestamp"`: Oldest first

**Returns:**
- Cleaned log structure with only essential fields:
  ```python
  {
      "logs": [
          {
              "timestamp": "2024-01-01T00:00:00Z",
              "message": "log message",
              "status": "info",
              "service": "service-name",
              "job_id": "...",  # Custom attributes included
          }
      ],
      "count": 10,
      "has_more": false
  }
  ```

**Example:**
```python
# Search for logs from a specific job in the last day
result = datadog_logs_search(query="job_id:abc-123", time_range="1d", limit=50)
print(f"Found {result['count']} logs")
for log in result['logs']:
    print(f"{log['timestamp']}: {log['message']}")

# Search for error logs from a service
datadog_logs_search(query="service:my-service status:error", time_range="6h")
```

### `datadog_search_events`
Search Datadog events with flexible time ranges and cursor-based pagination.

**Parameters:**
- `query` (string, optional): Event search query (default: `"*"`)
  - Examples: `"*"`, `"source:kubernetes"`, `"status:error"`
- `time_from` (string, optional): The minimum time for the requested events. Supports date math and regular timestamps in milliseconds. Default: `"now-1h"`
- `time_to` (string, optional): The maximum time for the requested events. Supports date math and regular timestamps in milliseconds. Default: `"now"`
- `limit` (integer, optional): Max events per page (default: 10, max: 1000)
- `sort` (string, optional): Sort order (default: `"-timestamp"` for newest first)
- `cursor` (string, optional): Pagination cursor from a previous response
- `timezone` (string, optional): Timezone for results, e.g. `"Europe/Amsterdam"`

**Returns:**
```python
{
    "events": [
        {
            "id": "...",
            "title": "Events from the Pod ...",
            "message": "...",
            "timestamp": "2026-04-13T15:47:07Z",
            "status": "warning",
            "priority": "normal",
            "source": "kubernetes_apiserver",
            "tags": [...]
        }
    ],
    "count": 10,
    "cursor": "eyJhZnRlci..."  # null if no more pages
}
```

**Example:**
```python
# Search events from the last 20 minutes
result = datadog_search_events(query="source:kubernetes", time_from="now-20m", time_to="now")

# Paginate through results
page1 = datadog_search_events(query="*", time_from="now-1h", limit=10)
if page1["cursor"]:
    page2 = datadog_search_events(query="*", time_from="now-1h", limit=10, cursor=page1["cursor"])
```

## Installation

### Prerequisites

- Python 3.6 or higher
- Datadog account with API access
- Datadog API key and Application key

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/velppa/datadog-mcp-server.git
   cd datadog-mcp-server
   ```

2. **Set up environment variables:**

   Add to your `~/.zshrc` or `~/.bashrc`:
   ```bash
   export DD_API_KEY="your_datadog_api_key"
   export DD_APP_KEY="your_datadog_application_key"
   export DD_SITE="datadoghq.com"  # or datadoghq.eu for EU
   ```

   Then reload your shell:
   ```bash
   source ~/.zshrc  # or source ~/.bashrc
   ```

3. **Get your Datadog credentials:**
   - Log in to [Datadog](https://app.datadoghq.com)
   - Navigate to **Organization Settings** → **API Keys** (for `DD_API_KEY`)
   - Navigate to **Organization Settings** → **Application Keys** (for `DD_APP_KEY`)
   - Create keys with required scopes: `cases_read`, `cases_write`

## Usage

### As an MCP Server (with Claude Code)

1. **Configure Claude Code:**

   Add to your Claude Code MCP configuration:
   ```json
   {
     "mcpServers": {
       "datadog": {
         "command": "python3",
         "args": ["/path/to/datadog-mcp-server/datadog_mcp_server.py"],
         "env": {
           "DD_API_KEY": "${DD_API_KEY}",
           "DD_APP_KEY": "${DD_APP_KEY}",
           "DD_SITE": "datadoghq.com"
         }
       }
     }
   }
   ```

2. **Restart Claude Code** to load the server

3. **Use the tools:**
   ```
   Ask Claude: "Search for open circuit breaker cases"
   Ask Claude: "Get details for Datadog case KEY-718"
   Ask Claude: "Add a comment to KEY-718 saying 'Investigation in progress'"
   Ask Claude: "Set KEY-718 status to IN_PROGRESS"
   Ask Claude: "Link KEY-792 as a duplicate of KEY-718"
   Ask Claude: "Search logs for job_id:abc-123 in the last day"
   Ask Claude: "Search events from the last 20 minutes"
   Ask Claude: "Search kubernetes events from now-1h to now-30m"
   ```

### As a Command-Line Tool

**Search cases:**
```bash
# Search for circuit breaker cases
python3 datadog_tools.py search "circuit breaker"

# Search with status filter
python3 datadog_tools.py search "circuit breaker status:open"

# Search only by status
python3 datadog_tools.py search "status:in_progress"
```

**Get case details:**
```bash
python3 datadog_tools.py get KEY-718
```

**Add a comment:**
```bash
python3 datadog_tools.py comment KEY-718 "This is a test comment"
```

**Set case status:**
```bash
# Set status to IN_PROGRESS
python3 datadog_tools.py status KEY-718 IN_PROGRESS

# Other valid statuses
python3 datadog_tools.py status KEY-718 OPEN
python3 datadog_tools.py status KEY-718 CLOSED
```

**Link cases:**
```bash
# Mark KEY-792 as duplicate of KEY-718
python3 datadog_tools.py link KEY-718 KEY-792 DUPLICATES

# Other relationship types
python3 datadog_tools.py link KEY-718 KEY-800 RELATES_TO
python3 datadog_tools.py link KEY-718 KEY-801 BLOCKS
```

**Search logs:**
```bash
# Search for logs from a specific job in the last day
python3 datadog_tools.py logs "job_id:abc-123" 1d 50

# Search for error logs in the last hour (default)
python3 datadog_tools.py logs "status:error"

# Search for service logs in the last 6 hours
python3 datadog_tools.py logs "service:my-service" 6h
```

### As a Python Module

```python
from datadog_tools import (
    datadog_search_cases,
    datadog_get_case,
    datadog_comment_case,
    datadog_set_case_status,
    datadog_link_cases,
    datadog_logs_search,
    datadog_search_events,
)

# Search for cases
results = datadog_search_cases(
    filter="circuit breaker status:open",
    page_size=50
)
print(f"Found {len(results['data'])} cases")

# Get case details
case_data = datadog_get_case("KEY-718")
print(f"Title: {case_data['data']['attributes']['title']}")
print(f"Status: {case_data['data']['attributes']['status']}")

# Add a comment
datadog_comment_case("KEY-718", "This is a test comment")

# Set case status
datadog_set_case_status("KEY-718", "IN_PROGRESS")

# Link cases
datadog_link_cases(
    parent_key="KEY-718",
    child_key="KEY-792",
    relationship="DUPLICATES"
)

# Search logs
logs = datadog_logs_search(
    query="job_id:abc-123",
    time_range="1d",
    limit=50
)
print(f"Found {logs['count']} logs")
for log in logs['logs']:
    print(f"{log['timestamp']}: {log['message']}")

# Search events
events = datadog_search_events(
    query="source:kubernetes",
    time_from="now-20m",
    time_to="now",
    limit=10,
)
print(f"Found {events['count']} events")
```

## Testing

### Test the MCP Server

```bash
# Initialize
echo '{"id":1,"method":"initialize","params":{}}' | python3 datadog_mcp_server.py

# List tools
echo '{"id":2,"method":"tools/list","params":{}}' | python3 datadog_mcp_server.py

# Call a tool
echo '{"id":3,"method":"tools/call","params":{"name":"datadog_get_case","arguments":{"key":"KEY-718"}}}' | python3 datadog_mcp_server.py
```

### Test Direct CLI

```bash
export DD_API_KEY="your_key"
export DD_APP_KEY="your_app_key"

python3 datadog_tools.py get KEY-718
```

## API Reference

See [DATADOG_TOOLS.md](DATADOG_TOOLS.md) for detailed API documentation.

## Architecture

```
datadog-mcp-server/
├── datadog_tools.py          # Core Datadog API functions
├── datadog_mcp_server.py     # MCP server implementation
├── DATADOG_SETUP.md          # Setup guide
├── DATADOG_TOOLS.md          # API reference
└── README.md                 # This file
```

### Implementation Details

- **No external dependencies** - Uses only Python standard library (`urllib`, `json`, `os`, `sys`)
- **Simple error handling** - Custom `DatadogAPIError` exception
- **Flexible configuration** - Environment variable based
- **MCP compliant** - Implements MCP protocol version 2024-11-05

## Troubleshooting

### Error: "DD_API_KEY environment variable not set"
Set the required environment variables:
```bash
export DD_API_KEY="your_api_key"
export DD_APP_KEY="your_app_key"
```

### Error: "Datadog API error: 401 Unauthorized"
- Verify your API key and Application key are correct
- Check that keys haven't expired
- Ensure Application key has required scopes (`cases_read`, `cases_write`)

### Error: "Datadog API error: 404 Not Found"
- Verify the case key is correct (e.g., `KEY-718`)
- Check that the case exists in Datadog
- Ensure you're using the correct `DD_SITE` (eu vs us)

### Error: "Network error"
- Check internet connectivity
- Verify `DD_SITE` is correct (`datadoghq.com` or `datadoghq.eu`)
- Check firewall/proxy settings

## Security Best Practices

- ✅ **Never commit API keys** to version control
- ✅ **Use environment variables** for credentials
- ✅ **Use scoped Application keys** with minimum required permissions
- ✅ **Rotate keys regularly** according to security policies
- ✅ **Revoke keys immediately** if compromised

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT

## Resources

- [Datadog Case Management API](https://docs.datadoghq.com/api/latest/case-management/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Datadog API Documentation](https://docs.datadoghq.com/api/)
- [Datadog API Authentication](https://docs.datadoghq.com/api/latest/authentication/)

## Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/velppa/datadog-mcp-server/issues)
- Check the [Datadog API documentation](https://docs.datadoghq.com/api/)
- Review [DATADOG_SETUP.md](DATADOG_SETUP.md) for configuration help
