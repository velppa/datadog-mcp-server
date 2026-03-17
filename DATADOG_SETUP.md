# Datadog MCP Setup Guide

This guide explains how to configure the Datadog MCP server for use
with the circuit-breaker-handler skill and other Content-MCP tools.

## Prerequisites

- Datadog account with access to FindHotel organization
- Permissions to create API keys and Application keys in Datadog

## Step 1: Obtain Datadog API Credentials

### 1.1 Get API Key

1. Log in to [Datadog](https://app.datadoghq.com)
2. Navigate to **Organization Settings** → **API Keys**
3. Create a new API key or use an existing one
4. Copy the API key value

### 1.2 Get Application Key

1. In Datadog, navigate to **Organization Settings** → **Application Keys**
2. Create a new Application key with the following scopes (at minimum):
   - `incidents_read` - Read incidents
   - `cases_read` - Read cases (if available)
   - `cases_write` - Write to cases (if available)
   - `monitors_read` - Read monitors
   - `dashboards_read` - Read dashboards
   - `logs_read_data` - Read log data
   - `events_read` - Read events
3. Copy the Application key value

## Step 2: Configure Environment Variables

Add your Datadog credentials to your environment. You have two options:

### Option A: Add to .env file (Local Development)

Add to `/Users/pavel/Developer/src/github.com/FindHotel/Content-MCP/.env`:

```bash
# Datadog API Credentials
DD_API_KEY=your_datadog_api_key_here
DD_APP_KEY=your_datadog_application_key_here
DD_SITE=datadoghq.com
```

**IMPORTANT**: The `.env` file is git-ignored. Never commit API keys to the repository!

### Option B: Add to shell profile (Global)

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
export DD_API_KEY="your_datadog_api_key_here"
export DD_APP_KEY="your_datadog_application_key_here"
export DD_SITE="datadoghq.com"
```

Then reload your shell:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

## Step 3: Verify Configuration

The Datadog MCP server is already configured in `.claude_config.json`:

```json
{
  "mcpServers": {
    "datadog": {
      "command": "datadog-mcp-server",
      "env": {
        "DD_API_KEY": "${DD_API_KEY}",
        "DD_APP_KEY": "${DD_APP_KEY}",
        "DD_SITE": "datadoghq.com"
      }
    }
  }
}
```

## Step 4: Test Connection

Restart Claude Code and test the Datadog connection:

```
Ask Claude: "List recent incidents from Datadog"
```

Claude should use the `get-incidents` tool from the Datadog MCP server to fetch incidents.

## Available Datadog MCP Tools

Once configured, the following tools are available:

### Monitoring & Alerting
- **get-monitors**: Retrieve monitors with filtering options
- **get-monitor**: Fetch specific monitor by ID

### Dashboards
- **get-dashboards**: List all dashboards
- **get-dashboard**: Retrieve specific dashboard by ID

### Metrics
- **get-metrics**: List available metrics
- **get-metric-metadata**: Get metadata for specific metric

### Incidents & Events
- **get-incidents**: List incidents with optional filtering
- **get-events**: Fetch events within timeframe

### Logs
- **search-logs**: Advanced log query searching
- **aggregate-logs**: Perform analytics and aggregations on log data

## Using Datadog with Circuit Breaker Skill

The circuit-breaker-handler skill is designed to work with Datadog cases created when circuit breakers open.

**Example workflow:**

1. Circuit breaker opens for a provider
2. Datadog creates a case (e.g., `KEY-718`)
3. Invoke the skill: `/circuit-breaker-handler KEY-718`
4. Claude investigates using Datadog and Snowflake tools
5. Claude updates the case with findings and resolution

## Troubleshooting

### Error: "Authentication failed"

- Verify your API key and Application key are correct
- Check that the keys have the required scopes
- Ensure environment variables are properly set

### Error: "datadog-mcp-server: command not found"

- The datadog-mcp-server is already installed globally
- Try reinstalling: `npm install -g datadog-mcp-server`
- Check npm global bin path: `npm bin -g`

### Error: "Unable to connect to Datadog"

- Verify `DD_SITE` is set to `datadoghq.com`

- If using US region, change to `datadoghq.com`
- Check network connectivity to Datadog

## Security Best Practices

1. **Never commit API keys** to git repositories
2. **Use scoped Application keys** with minimum required permissions
3. **Rotate keys regularly** following FindHotel security policies
4. **Store keys securely** in environment variables or secrets manager
5. **Revoke keys immediately** if compromised

## Additional Resources

- [Datadog API Documentation](https://docs.datadoghq.com/api/)
- [Datadog Case Management](https://docs.datadoghq.com/service_management/case_management/)
- [datadog-mcp-server GitHub](https://github.com/GeLi2001/datadog-mcp-server)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## Support

For issues with:
- **Datadog access**: Contact FindHotel IT or Datadog admin
- **API key permissions**: Contact Datadog admin
- **Circuit breaker skill**: See `skills/circuit-breaker-handler/README.md`
- **MCP configuration**: Check `.claude_config.json` and this guide
