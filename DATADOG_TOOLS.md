# Datadog Case Management Tools

Python-based tools for interacting with Datadog Case Management API, integrated as an MCP server for Claude Code.

## Overview

This implementation provides two core functions for Datadog case management:

1. **`datadog_get_case(key)`** - Retrieve details of a case by its key
2. **`datadog_link_cases(parent_key, child_key, relationship)`** - Create relationships between cases

These tools use **only Python standard library** (no external dependencies) and are exposed via a Model Context Protocol (MCP) server.

## Setup

### 1. Set Environment Variables

The tools require Datadog API credentials:

```bash
export DD_API_KEY="your_datadog_api_key"
export DD_APP_KEY="your_datadog_application_key"
export DD_SITE="datadoghq.com"  # or datadoghq.com for US
```

**Where to get credentials:**
1. Log in to [Datadog](https://app.datadoghq.com)
2. Navigate to **Organization Settings** → **API Keys** (for DD_API_KEY)
3. Navigate to **Organization Settings** → **Application Keys** (for DD_APP_KEY)
4. Create keys with appropriate scopes: `cases_read`, `cases_write`

### 2. MCP Server Configuration

The Datadog MCP server is already configured in `.claude_config.json`:

```json
{
  "mcpServers": {
    "datadog_case_management": {
      "command": "python3",
      "args": [
        "/Users/pavel/Developer/src/github.com/FindHotel/Content-MCP/datadog_mcp_server.py"
      ],
      "env": {
        "DD_API_KEY": "${DD_API_KEY}",
        "DD_APP_KEY": "${DD_APP_KEY}",
        "DD_SITE": "datadoghq.com"
      }
    }
  }
}
```

## Usage

### Via MCP (Claude Code)

Once configured, Claude Code can access these tools:

**Get a case:**
```
Claude will use: datadog_get_case(key="CONTENT-718")
```

**Link cases:**
```
Claude will use: datadog_link_cases(
    parent_key="CONTENT-718",
    child_key="CONTENT-792",
    relationship="DUPLICATES"
)
```

### Direct Command Line

You can also use the tools directly from the command line:

**Get case details:**
```bash
python3 datadog_tools.py get CONTENT-718
```

**Link two cases:**
```bash
# Mark CONTENT-792 as duplicate of CONTENT-718
python3 datadog_tools.py link CONTENT-718 CONTENT-792 DUPLICATES

# Other relationship types
python3 datadog_tools.py link CONTENT-718 CONTENT-800 RELATES_TO
python3 datadog_tools.py link CONTENT-718 CONTENT-801 BLOCKS
```

### As Python Module

Import and use directly in Python code:

```python
from datadog_tools import datadog_get_case, datadog_link_cases

# Get case details
case_data = datadog_get_case("CONTENT-718")
print(f"Title: {case_data['data']['attributes']['title']}")
print(f"Status: {case_data['data']['attributes']['status']}")

# Link cases
result = datadog_link_cases(
    parent_key="CONTENT-718",
    child_key="CONTENT-792",
    relationship="DUPLICATES"
)
print("Cases linked successfully!")
```

## API Reference

### `datadog_get_case(key: str) -> Dict[str, Any]`

Retrieves detailed information about a Datadog case.

**Parameters:**
- `key` (str): Case key, e.g., `"CONTENT-718"`

**Returns:**
- Dictionary with case details including:
  - `data.id`: Internal case UUID
  - `data.attributes.key`: Case key (CONTENT-XXX)
  - `data.attributes.title`: Case title
  - `data.attributes.description`: Case description
  - `data.attributes.status`: Case status
  - `data.attributes.priority`: Case priority
  - `data.relationships`: Related entities

**Example Response:**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "case",
    "attributes": {
      "key": "CONTENT-718",
      "title": "Circuit breaker opened for AGD provider",
      "description": "...",
      "status": "IN_PROGRESS",
      "priority": "P2"
    }
  }
}
```

**Raises:**
- `DatadogAPIError`: If case not found or API error occurs

### `datadog_link_cases(parent_key: str, child_key: str, relationship: str = "DUPLICATES") -> Dict[str, Any]`

Creates a relationship between two Datadog cases.

**Parameters:**
- `parent_key` (str): Parent case key, e.g., `"CONTENT-718"`
- `child_key` (str): Child case key, e.g., `"CONTENT-792"`
- `relationship` (str, optional): Relationship type. Default: `"DUPLICATES"`

**Valid Relationship Types:**
- `"DUPLICATES"`: Child is a duplicate of parent
- `"RELATES_TO"`: Child relates to parent
- `"BLOCKS"`: Child blocks parent
- (Other types may be supported by Datadog API)

**Returns:**
- Dictionary with link creation confirmation

**How it works:**
1. Retrieves both parent and child cases to get internal IDs
2. Creates a link between them with specified relationship
3. Returns the created link details

**Example:**
```python
# Mark CONTENT-792 as duplicate of CONTENT-718
datadog_link_cases("CONTENT-718", "CONTENT-792", "DUPLICATES")

# Indicate CONTENT-800 relates to CONTENT-718
datadog_link_cases("CONTENT-718", "CONTENT-800", "RELATES_TO")
```

**Raises:**
- `DatadogAPIError`: If either case not found or API error occurs

## Implementation Details

### Architecture

```
datadog_tools.py
├── datadog_get_case()          # Core API function
├── datadog_link_cases()        # Core API function
├── _make_request()             # HTTP request handler
├── _get_headers()              # Auth headers builder
└── _get_base_url()             # URL builder

datadog_mcp_server.py
├── MCPServer class             # MCP protocol implementation
├── handle_initialize()         # MCP initialization
├── handle_list_tools()         # Tool discovery
└── handle_call_tool()          # Tool execution
```

### No External Dependencies

The implementation uses **only Python standard library**:
- `urllib.request` - HTTP requests
- `json` - JSON parsing/encoding
- `os` - Environment variables
- `sys` - I/O and command-line args

This ensures:
- ✅ No dependency installation required
- ✅ Works with system Python 3
- ✅ Fast startup time
- ✅ Minimal maintenance burden

### Error Handling

All functions raise `DatadogAPIError` with descriptive messages:

```python
from datadog_tools import DatadogAPIError

try:
    case = datadog_get_case("CONTENT-999")
except DatadogAPIError as e:
    print(f"Error: {e}")
    # Error: Datadog API error: 404 Not Found
```

## Testing

### Manual Test

Test the tools with a known case:

```bash
# Set credentials
export DD_API_KEY="your_key"
export DD_APP_KEY="your_app_key"

# Test get_case
python3 datadog_tools.py get CONTENT-718

# Test link_cases (be careful - this modifies Datadog!)
# python3 datadog_tools.py link CONTENT-718 CONTENT-792 DUPLICATES
```

### MCP Server Test

Test the MCP server by sending JSON-RPC requests:

```bash
echo '{"id":1,"method":"initialize","params":{}}' | python3 datadog_mcp_server.py
echo '{"id":2,"method":"tools/list","params":{}}' | python3 datadog_mcp_server.py
```

## Files

- **`datadog_tools.py`** - Core Datadog API functions
- **`datadog_mcp_server.py`** - MCP server wrapper
- **`.claude_config.json`** - MCP server configuration
- **`DATADOG_TOOLS.md`** - This documentation

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

- Verify the case key is correct (e.g., `CONTENT-718`)
- Check that the case exists in Datadog
- Ensure you're using the correct DD_SITE (eu vs us)

### Error: "Network error: Name or service not known"

- Check internet connectivity
- Verify DD_SITE is correct (`datadoghq.com` or `datadoghq.eu`)
- Check firewall/proxy settings

## Security

- **Never commit API keys** to version control
- Store credentials in environment variables or secrets manager
- Use scoped Application keys with minimum required permissions
- Rotate keys regularly according to security policies

## References

- [Datadog Case Management API](https://docs.datadoghq.com/api/latest/case-management/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Datadog API Authentication](https://docs.datadoghq.com/api/latest/authentication/)

## Support

For issues:
- **Datadog API**: Check [Datadog API docs](https://docs.datadoghq.com/api/)
- **MCP Server**: See [MCP specification](https://modelcontextprotocol.io/)
- **Circuit breaker skill**: See `skills/circuit-breaker-handler/README.md`
