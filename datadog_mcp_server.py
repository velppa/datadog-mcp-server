#!/usr/bin/env python3
"""
Datadog MCP Server

Model Context Protocol server that exposes Datadog Case Management tools.
Implements the MCP protocol for use with Claude Code and other MCP clients.
"""

import json
import sys
from typing import Any, Dict, List

from datadog_tools import (
    datadog_search_cases,
    datadog_get_case,
    datadog_create_case,
    datadog_comment_case,
    datadog_set_case_status,
    datadog_link_cases,
    datadog_assign_case,
    datadog_unassign_case,
    datadog_logs_search,
    datadog_search_events,
    DatadogAPIError
)


class MCPServer:
    """Simple MCP server implementation for Datadog tools."""

    def __init__(self):
        self.tools = {
            "datadog_search_cases": {
                "description": "Search Datadog cases with server-side filtering. Filter supports free text and field prefixes like status:open. Examples: 'circuit breaker mapping-pipeline status:open', 'status:in_progress', 'API error status:open'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Search query. Free text + optional prefixes: status:open, status:in_progress, status:closed. Example: 'circuit breaker mapping-pipeline status:open'"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Cases per page (default 100, max 100)",
                            "default": 100
                        },
                        "page_number": {
                            "type": "integer",
                            "description": "Page number, 1-based (default 1)",
                            "default": 1
                        },
                        "sort_field": {
                            "type": "string",
                            "description": "Sort field",
                            "enum": ["created_at", "priority", "status"],
                            "default": "created_at"
                        },
                        "sort_asc": {
                            "type": "boolean",
                            "description": "Sort ascending (default false = newest first)",
                            "default": False
                        }
                    },
                    "required": []
                }
            },
            "datadog_get_case": {
                "description": "Get details (including comments) of a Datadog case by its key (e.g., KEY-718)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Case key (e.g., 'KEY-718')"
                        }
                    },
                    "required": ["key"]
                }
            },
            "datadog_create_case": {
                "description": "Create a new Datadog case in a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Case title"
                        },
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., 'CONTENT', 'MON')"
                        },
                        "case_type": {
                            "type": "string",
                            "description": "Case type name",
                            "enum": ["Standard", "Event Management", "Security", "Change Request", "Error Tracking", "Logs Optimization Insights"],
                            "default": "Standard"
                        },
                        "description": {
                            "type": "string",
                            "description": "Case description (optional)"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Case priority",
                            "enum": ["NOT_DEFINED", "P1", "P2", "P3", "P4", "P5"],
                            "default": "NOT_DEFINED"
                        },
                        "assignee_id": {
                            "type": "string",
                            "description": "User UUID to assign the case to (optional)"
                        }
                    },
                    "required": ["title", "project_key"]
                }
            },
            "datadog_comment_case": {
                "description": "Add a comment to a Datadog case",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Case key (e.g., 'KEY-718')"
                        },
                        "comment": {
                            "type": "string",
                            "description": "Comment text to add to the case"
                        }
                    },
                    "required": ["key", "comment"]
                }
            },
            "datadog_set_case_status": {
                "description": "Set the status of a Datadog case",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Case key (e.g., 'KEY-718')"
                        },
                        "status": {
                            "type": "string",
                            "description": "Case status",
                            "enum": ["IN_PROGRESS", "OPEN", "CLOSED"]
                        }
                    },
                    "required": ["key", "status"]
                }
            },
            "datadog_link_cases": {
                "description": "Create a relationship between two Datadog cases",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "parent_key": {
                            "type": "string",
                            "description": "Parent case key (e.g., 'KEY-718')"
                        },
                        "child_key": {
                            "type": "string",
                            "description": "Child case key (e.g., 'KEY-792')"
                        },
                        "relationship": {
                            "type": "string",
                            "description": "Relationship type",
                            "enum": ["DUPLICATES", "RELATES_TO", "BLOCKS"],
                            "default": "DUPLICATES"
                        }
                    },
                    "required": ["parent_key", "child_key"]
                }
            },
            "datadog_assign_case": {
                "description": "Assign a Datadog case to a user by their Datadog user UUID. Use this to make someone the case owner (e.g. escalate to a partnerships contact). UUID is required — fetch from /api/v2/cases/{key} relationships.assignee.data.id after a one-time UI assignment if unknown.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Case key (e.g., 'KEY-718')"
                        },
                        "assignee_id": {
                            "type": "string",
                            "description": "Assignee's Datadog user UUID (e.g., 'ec34f974-2c51-11ee-bc35-7a3adbb5cabc')"
                        }
                    },
                    "required": ["key", "assignee_id"]
                }
            },
            "datadog_unassign_case": {
                "description": "Remove the current assignee from a Datadog case (sets assignee to null).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Case key (e.g., 'KEY-718')"
                        }
                    },
                    "required": ["key"]
                }
            },
            "datadog_logs_search": {
                "description": "Search Datadog logs with a query. Supports queries like 'job_id:<uuid>' or 'service:my-service status:error'. Time range examples: '1h' (last hour), '1d' (last day), '30m' (last 30 minutes).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Log search query (e.g., 'job_id:abc-123', 'service:my-service status:error', '*' for all)"
                        },
                        "time_range": {
                            "type": "string",
                            "description": "Time range for search: '1h', '1d', '7d', '30m', etc. (default: '1h')",
                            "default": "1h"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of logs to return (default: 100, max: 1000)",
                            "default": 100,
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "sort": {
                            "type": "string",
                            "description": "Sort order: '-timestamp' (newest first) or 'timestamp' (oldest first)",
                            "enum": ["-timestamp", "timestamp"],
                            "default": "-timestamp"
                        }
                    },
                    "required": ["query"]
                }
            },
            "datadog_search_events": {
                "description": "Search Datadog events using the events search API (POST). Supports flexible time ranges like 'now-20m' to 'now-10m', pagination via cursor, and timezone options.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Event search query (e.g., '*', 'source:kubernetes', 'status:error')",
                            "default": "*"
                        },
                        "time_from": {
                            "type": "string",
                            "description": "The minimum time for the requested events. Supports date math and regular timestamps in milliseconds. Default: 'now-1h'",
                            "default": "now-1h"
                        },
                        "time_to": {
                            "type": "string",
                            "description": "The maximum time for the requested events. Supports date math and regular timestamps in milliseconds. Default: 'now'",
                            "default": "now"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max events per page (default: 10, max: 1000)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "sort": {
                            "type": "string",
                            "description": "Sort order: '-timestamp' (newest first) or 'timestamp' (oldest first)",
                            "enum": ["-timestamp", "timestamp"],
                            "default": "-timestamp"
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor from a previous response (optional)"
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone for results, e.g. 'Europe/Amsterdam' (optional)"
                        }
                    },
                    "required": []
                }
            }
        }

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "datadog-case-management",
                "version": "1.0.0"
            }
        }

    def handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tools/list request."""
        tools_list = []
        for name, tool_info in self.tools.items():
            tools_list.append({
                "name": name,
                "description": tool_info["description"],
                "inputSchema": tool_info["inputSchema"]
            })

        return {"tools": tools_list}

    def handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "datadog_search_cases":
                result = datadog_search_cases(
                    filter=arguments.get("filter"),
                    page_size=arguments.get("page_size", 100),
                    page_number=arguments.get("page_number", 1),
                    sort_field=arguments.get("sort_field", "created_at"),
                    sort_asc=arguments.get("sort_asc", False),
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            elif tool_name == "datadog_get_case":
                key = arguments.get("key")
                if not key:
                    raise ValueError("Missing required argument: key")

                result = datadog_get_case(key)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            elif tool_name == "datadog_create_case":
                title = arguments.get("title")
                project_key = arguments.get("project_key")

                if not title:
                    raise ValueError("Missing required argument: title")
                if not project_key:
                    raise ValueError("Missing required argument: project_key")

                result = datadog_create_case(
                    title=title,
                    project_key=project_key,
                    case_type=arguments.get("case_type", "Standard"),
                    description=arguments.get("description", ""),
                    priority=arguments.get("priority", "NOT_DEFINED"),
                    assignee_id=arguments.get("assignee_id"),
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            elif tool_name == "datadog_comment_case":
                key = arguments.get("key")
                comment = arguments.get("comment")

                if not key:
                    raise ValueError("Missing required argument: key")
                if not comment:
                    raise ValueError("Missing required argument: comment")

                result = datadog_comment_case(key, comment)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            elif tool_name == "datadog_set_case_status":
                key = arguments.get("key")
                status = arguments.get("status")

                if not key:
                    raise ValueError("Missing required argument: key")
                if not status:
                    raise ValueError("Missing required argument: status")

                result = datadog_set_case_status(key, status)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            elif tool_name == "datadog_link_cases":
                parent_key = arguments.get("parent_key")
                child_key = arguments.get("child_key")
                relationship = arguments.get("relationship", "DUPLICATES")

                if not parent_key:
                    raise ValueError("Missing required argument: parent_key")
                if not child_key:
                    raise ValueError("Missing required argument: child_key")

                result = datadog_link_cases(parent_key, child_key, relationship)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            elif tool_name == "datadog_assign_case":
                key = arguments.get("key")
                assignee_id = arguments.get("assignee_id")

                if not key:
                    raise ValueError("Missing required argument: key")
                if not assignee_id:
                    raise ValueError("Missing required argument: assignee_id")

                result = datadog_assign_case(key, assignee_id)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            elif tool_name == "datadog_unassign_case":
                key = arguments.get("key")

                if not key:
                    raise ValueError("Missing required argument: key")

                result = datadog_unassign_case(key)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            elif tool_name == "datadog_logs_search":
                query = arguments.get("query")
                time_range = arguments.get("time_range", "1h")
                limit = arguments.get("limit", 100)
                sort = arguments.get("sort", "-timestamp")

                if not query:
                    raise ValueError("Missing required argument: query")

                result = datadog_logs_search(query, time_range, limit, sort)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            elif tool_name == "datadog_search_events":
                result = datadog_search_events(
                    query=arguments.get("query", "*"),
                    time_from=arguments.get("time_from", "now-1h"),
                    time_to=arguments.get("time_to", "now"),
                    limit=arguments.get("limit", 10),
                    sort=arguments.get("sort", "-timestamp"),
                    cursor=arguments.get("cursor"),
                    timezone=arguments.get("timezone"),
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except (DatadogAPIError, ValueError) as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route incoming MCP requests to appropriate handlers."""
        method = request.get("method")
        params = request.get("params", {})

        handlers = {
            "initialize": self.handle_initialize,
            "tools/list": self.handle_list_tools,
            "tools/call": self.handle_call_tool,
        }

        handler = handlers.get(method)
        if handler:
            return {"result": handler(params)}

        # Notifications are silently ignored
        if method and method.startswith("notifications/"):
            return None

        return {
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

    def _send(self, response: Dict[str, Any]):
        """Send a JSON-RPC 2.0 response."""
        response["jsonrpc"] = "2.0"
        print(json.dumps(response), flush=True)

    def run(self):
        """Run the MCP server (stdio mode)."""
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = self.handle_request(request)

                # Notifications (no id) and ignored methods get no response
                if response is None or "id" not in request:
                    continue

                response["id"] = request["id"]
                self._send(response)

            except json.JSONDecodeError as e:
                self._send({
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {e}"
                    }
                })
            except Exception as e:
                self._send({
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {e}"
                    }
                })


def main():
    """Main entry point for the MCP server."""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
