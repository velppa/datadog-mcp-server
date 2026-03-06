# Datadog MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides Datadog Case Management integration for Claude Code and other MCP clients.

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
    filter="circuit breaker mapping-pipeline status:open",
    page_size=50
)

# Get all in-progress cases
datadog_search_cases(filter="status:in_progress")
```

### `datadog_get_case`
Retrieve detailed information about a Datadog case by its key.

**Parameters:**
- `key` (string): Case key, e.g., `"CONTENT-718"`

**Example:**
```python
datadog_get_case(key="CONTENT-718")
```

### `datadog_comment_case`
Add a comment to a Datadog case.

**Parameters:**
- `key` (string): Case key, e.g., `"CONTENT-718"`
- `comment` (string): Comment text to add to the case

**Example:**
```python
datadog_comment_case(
    key="CONTENT-718",
    comment="This is a test comment"
)
```

### `datadog_set_case_status`
Set the status of a Datadog case.

**Parameters:**
- `key` (string): Case key, e.g., `"CONTENT-718"`
- `status` (string): Case status - must be one of:
  - `"IN_PROGRESS"` - Case is being worked on
  - `"OPEN"` - Case is open and awaiting action
  - `"CLOSED"` - Case is closed

**Example:**
```python
datadog_set_case_status(
    key="CONTENT-718",
    status="IN_PROGRESS"
)
```

### `datadog_link_cases`
Create a relationship between two Datadog cases.

**Parameters:**
- `parent_key` (string): Parent case key, e.g., `"CONTENT-718"`
- `child_key` (string): Child case key, e.g., `"CONTENT-792"`
- `relationship` (string): Relationship type (default: `"DUPLICATES"`)
  - Valid values: `"DUPLICATES"`, `"RELATES_TO"`, `"BLOCKS"`

**Example:**
```python
datadog_link_cases(
    parent_key="CONTENT-718",
    child_key="CONTENT-792",
    relationship="DUPLICATES"
)
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
   Ask Claude: "Get details for Datadog case CONTENT-718"
   Ask Claude: "Add a comment to CONTENT-718 saying 'Investigation in progress'"
   Ask Claude: "Set CONTENT-718 status to IN_PROGRESS"
   Ask Claude: "Link CONTENT-792 as a duplicate of CONTENT-718"
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
python3 datadog_tools.py get CONTENT-718
```

**Add a comment:**
```bash
python3 datadog_tools.py comment CONTENT-718 "This is a test comment"
```

**Set case status:**
```bash
# Set status to IN_PROGRESS
python3 datadog_tools.py status CONTENT-718 IN_PROGRESS

# Other valid statuses
python3 datadog_tools.py status CONTENT-718 OPEN
python3 datadog_tools.py status CONTENT-718 CLOSED
```

**Link cases:**
```bash
# Mark CONTENT-792 as duplicate of CONTENT-718
python3 datadog_tools.py link CONTENT-718 CONTENT-792 DUPLICATES

# Other relationship types
python3 datadog_tools.py link CONTENT-718 CONTENT-800 RELATES_TO
python3 datadog_tools.py link CONTENT-718 CONTENT-801 BLOCKS
```

### As a Python Module

```python
from datadog_tools import (
    datadog_search_cases,
    datadog_get_case,
    datadog_comment_case,
    datadog_set_case_status,
    datadog_link_cases
)

# Search for cases
results = datadog_search_cases(
    filter="circuit breaker status:open",
    page_size=50
)
print(f"Found {len(results['data'])} cases")

# Get case details
case_data = datadog_get_case("CONTENT-718")
print(f"Title: {case_data['data']['attributes']['title']}")
print(f"Status: {case_data['data']['attributes']['status']}")

# Add a comment
datadog_comment_case("CONTENT-718", "This is a test comment")

# Set case status
datadog_set_case_status("CONTENT-718", "IN_PROGRESS")

# Link cases
datadog_link_cases(
    parent_key="CONTENT-718",
    child_key="CONTENT-792",
    relationship="DUPLICATES"
)
```

## Testing

### Test the MCP Server

```bash
# Initialize
echo '{"id":1,"method":"initialize","params":{}}' | python3 datadog_mcp_server.py

# List tools
echo '{"id":2,"method":"tools/list","params":{}}' | python3 datadog_mcp_server.py

# Call a tool
echo '{"id":3,"method":"tools/call","params":{"name":"datadog_get_case","arguments":{"key":"CONTENT-718"}}}' | python3 datadog_mcp_server.py
```

### Test Direct CLI

```bash
export DD_API_KEY="your_key"
export DD_APP_KEY="your_app_key"

python3 datadog_tools.py get CONTENT-718
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
- Verify the case key is correct (e.g., `CONTENT-718`)
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
