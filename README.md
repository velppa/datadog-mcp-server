# Datadog MCP Server

This [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
server that provides Datadog integration for Claude Code and other MCP
clients.  The focus is on Case Management, Events and Logging
capabilities.

The official [Datadog MCP Server](https://www.datadoghq.com/blog/datadog-remote-mcp-server/) implements very limited subset of tools.

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

Tool names, parameters, and schemas are exposed by the MCP server itself.
List them with `tools/list` or via your MCP client's tool browser. The
CLI prints its own usage when run with no arguments:

```bash
python3 datadog_tools.py
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

2. **Get your Datadog credentials:**
   - Log in to [Datadog](https://app.datadoghq.com)
   - **Organization Settings → API Keys** — create/reuse for `DD_API_KEY`
   - **Organization Settings → Application Keys** — create for `DD_APP_KEY`
     with minimum scopes:
     - `cases_read`, `cases_write` — case management
     - `user_access_read` — user lookup
     - `logs_read_data` — log search
     - `events_read` — event search

3. **Set up environment variables.** Either export them in your shell
   profile (`~/.zshrc` / `~/.bashrc`):
   ```bash
   export DD_API_KEY="your_datadog_api_key"
   export DD_APP_KEY="your_datadog_application_key"
   export DD_SITE="datadoghq.com"  # or datadoghq.eu, us3.datadoghq.com, ...
   ```
   …or put them in a git-ignored `.env` file next to the server. Never
   commit credentials.

## Usage

### As an MCP Server (with Claude Code)

1. **Configure Claude Code:**

   Add to your MCP client config (e.g., `~/.claude.json`):
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

3. **Use the tools** — ask your MCP client to invoke them by name, or
   discover them via the client's tool browser.

### As a Command-Line Tool

```bash
python3 datadog_tools.py             # prints subcommand usage
python3 datadog_tools.py <subcommand> [args...]
```

### As a Python Module

Import the functions you need from `datadog_tools` and call them
directly. See each function's docstring for arguments and return shape.

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

## Architecture

```
datadog-mcp-server/
├── datadog_tools.py          # Core Datadog API functions
├── datadog_mcp_server.py     # MCP server implementation
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
