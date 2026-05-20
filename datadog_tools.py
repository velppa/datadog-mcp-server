#!/usr/bin/env python3
"""
Datadog Case Management Tools

Provides functions to interact with Datadog Case Management API.
Uses only Python standard library (no external dependencies).

Environment Variables Required:
- DD_API_KEY: Datadog API key
- DD_APP_KEY: Datadog Application key
- DD_SITE: Datadog site (default: datadoghq.com)
"""

import json
import os
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Optional


class DatadogAPIError(Exception):
    """Exception raised for Datadog API errors."""
    pass


def _get_headers() -> Dict[str, str]:
    """
    Get Datadog API headers with authentication.

    Returns:
        Dict with required headers for Datadog API calls

    Raises:
        DatadogAPIError: If required environment variables are not set
    """
    api_key = os.getenv("DD_API_KEY")
    app_key = os.getenv("DD_APP_KEY")

    if not api_key:
        raise DatadogAPIError("DD_API_KEY environment variable not set")
    if not app_key:
        raise DatadogAPIError("DD_APP_KEY environment variable not set")

    return {
        "Content-Type": "application/json",
        "DD-API-KEY": api_key,
        "DD-APPLICATION-KEY": app_key,
    }


def _get_base_url() -> str:
    """
    Get Datadog API base URL based on DD_SITE environment variable.

    Returns:
        Base URL for Datadog API.
    """
    site = os.getenv("DD_SITE", "datadoghq.com")
    return f"https://api.{site}"


def _make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Make an HTTP request to Datadog API.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        data: Optional request body data

    Returns:
        JSON response as dictionary

    Raises:
        DatadogAPIError: If the API request fails
    """
    url = f"{_get_base_url()}{endpoint}"
    headers = _get_headers()

    # Prepare request
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode('utf-8')

    request = urllib.request.Request(
        url,
        data=req_data,
        headers=headers,
        method=method
    )

    try:
        with urllib.request.urlopen(request) as response:
            response_data = response.read().decode('utf-8')
            return json.loads(response_data)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise DatadogAPIError(
            f"Datadog API error: {e.code} {e.reason}\n{error_body}"
        )
    except urllib.error.URLError as e:
        raise DatadogAPIError(f"Network error: {e.reason}")
    except json.JSONDecodeError as e:
        raise DatadogAPIError(f"Invalid JSON response: {e}")


def _format_case_summary(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a case for cleaner output by promoting team to top level.

    Args:
        case: Raw case data from Datadog API

    Returns:
        Formatted case with team at top level and all other attributes preserved
    """
    attrs = case.get("attributes", {})

    # Start with all attributes
    result = dict(attrs)

    # Extract team from nested attributes and promote to top level
    nested_attrs = attrs.get("attributes", {})
    if "team" in nested_attrs:
        result["team"] = nested_attrs["team"]

    return result


def datadog_search_cases(
    filter: str = None,
    page_size: int = 100,
    page_number: int = 1,
    sort_field: str = "created_at",
    sort_asc: bool = False
) -> Dict[str, Any]:
    """
    Search Datadog cases with server-side filtering.

    Args:
        filter: Search query string. Supports free text and field prefixes.
                Examples:
                  - "circuit breaker" — text search in title/description
                  - "circuit breaker status:open" — text + status filter
                  - "circuit breaker mapping-pipeline status:open" — narrow to mapping CBs
                  - "status:open" / "status:in_progress" / "status:closed"
                  - "status:open,in_progress" — multiple statuses (makes 2 API calls internally)
        page_size: Number of cases per page (max 100).
        page_number: Page number (1-based).
        sort_field: Sort field: "created_at", "priority", or "status".
        sort_asc: Sort ascending (False = newest first).

    Returns:
        Dictionary with cases list and pagination meta:
        {
            "cases": [
                {
                    "key": "KEY-123",
                    "title": "Case title",
                    "status": "OPEN",
                    "priority": "NOT_DEFINED",
                    "created_at": "2026-03-07T18:09:15Z",
                    "team": ["content"],
                    "attributes": {
                        "env": ["production"],
                        "statemachinename": ["image-download-prod"],
                        ...
                    },
                    ... (all other case attributes)
                },
                ...
            ],
            "total_count": 42,
            "page": 1,
            "page_size": 100
        }
    """
    import urllib.parse
    import re

    # Check if filter contains multiple statuses (e.g., "status:open,in_progress")
    multi_status_match = re.search(r'status:(\w+(?:,\w+)+)', filter or '')

    if multi_status_match:
        # Extract the comma-separated statuses
        statuses = multi_status_match.group(1).split(',')

        # Remove the multi-status part from the filter
        base_filter = re.sub(r'status:\w+(?:,\w+)+', '', filter).strip()

        # Make separate API calls for each status
        all_cases = []
        total_count = 0

        for status in statuses:
            # Build filter with single status
            status_filter = f"status:{status.strip()}"
            if base_filter:
                status_filter = f"{base_filter} {status_filter}"

            params = {
                "page[size]": str(page_size),
                "page[number]": str(page_number),
                "sort[field]": sort_field,
                "sort[asc]": str(sort_asc).lower(),
                "filter": status_filter
            }

            query_string = urllib.parse.urlencode(params)
            endpoint = f"/api/v2/cases?{query_string}"
            raw_result = _make_request("GET", endpoint)

            # Extract and clean case data
            cases = raw_result.get("data", [])
            cleaned_cases = [_format_case_summary(case) for case in cases]
            all_cases.extend(cleaned_cases)

            # Accumulate total count
            meta = raw_result.get("meta", {})
            total_count += meta.get("total_cases", len(cleaned_cases))

        # Deduplicate cases by key (in case a case appears in multiple status results)
        seen_keys = set()
        unique_cases = []
        for case in all_cases:
            case_key = case.get("key")
            if case_key and case_key not in seen_keys:
                seen_keys.add(case_key)
                unique_cases.append(case)

        return {
            "cases": unique_cases,
            "total_count": len(unique_cases),
            "page": page_number,
            "page_size": len(unique_cases)
        }

    # Single status or no status filter - use original logic
    params = {
        "page[size]": str(page_size),
        "page[number]": str(page_number),
        "sort[field]": sort_field,
        "sort[asc]": str(sort_asc).lower(),
    }
    if filter:
        params["filter"] = filter

    query_string = urllib.parse.urlencode(params)
    endpoint = f"/api/v2/cases?{query_string}"
    raw_result = _make_request("GET", endpoint)

    # Extract and clean case data
    cases = raw_result.get("data", [])
    cleaned_cases = [_format_case_summary(case) for case in cases]

    # Extract pagination info
    meta = raw_result.get("meta", {})

    return {
        "cases": cleaned_cases,
        "total_count": meta.get("total_cases", len(cleaned_cases)),
        "page": page_number,
        "page_size": len(cleaned_cases)
    }


def datadog_get_case(key: str) -> Dict[str, Any]:
    """
    Get details of a Datadog case by its key.

    Args:
        key: Case key (e.g., "KEY-718")

    Returns:
        Dictionary containing case details with structure:
        {
            "data": {
                "id": "case_uuid",
                "type": "case",
                "attributes": {
                    "key": "KEY-718",
                    "title": "...",
                    "description": "...",
                    "status": "...",
                    "priority": "...",
                    ...
                },
                "relationships": {...}
            }
        }

    Raises:
        DatadogAPIError: If the API request fails or case not found

    Example:
        >>> case_data = datadog_get_case("KEY-718")
        >>> print(case_data['data']['attributes']['title'])
    """
    endpoint = f"/api/v2/cases/{key}"
    case_data = _make_request("GET", endpoint)

    timeline_endpoint = f"/api/v2/cases/{key}/timelines"
    timeline_data = _make_request("GET", timeline_endpoint)
    comments = []
    for entry in timeline_data.get("data", []):
        attrs = entry.get("attributes", {})
        if attrs.get("type") == "COMMENT":
            author = attrs.get("author", {}).get("content", {})
            comments.append({
                "id": entry.get("id"),
                "message": attrs.get("cell_content", {}).get("message", ""),
                "created_at": attrs.get("created_at"),
                "author": author.get("name") or author.get("email", ""),
            })
    case_data["comments"] = comments

    # Override the API's comment_count (always 0) with actual count
    if "data" in case_data and "attributes" in case_data["data"]:
        case_data["data"]["attributes"]["comment_count"] = len(comments)

    return case_data


def _get_case_type_id(case_type: str) -> str:
    """
    Resolve a case type name (e.g., "Standard") to its UUID.

    Args:
        case_type: Case type name (e.g., "Standard", "Security", "Change Request")

    Returns:
        Case type UUID string

    Raises:
        DatadogAPIError: If the API request fails or case type not found
    """
    result = _make_request("GET", "/api/v2/cases/types")
    for ct in result.get("data", []):
        if ct.get("attributes", {}).get("name", "").lower() == case_type.lower():
            return ct["id"]
    available = [t["attributes"]["name"] for t in result.get("data", []) if "attributes" in t]
    raise DatadogAPIError(
        f"Case type '{case_type}' not found. Available types: {', '.join(available)}"
    )


def _get_project_id(project_key: str) -> str:
    """
    Resolve a project key (e.g., "CONTENT") to its UUID.

    Args:
        project_key: Project key (e.g., "CONTENT", "MON")

    Returns:
        Project UUID string

    Raises:
        DatadogAPIError: If the API request fails or project not found
    """
    result = _make_request("GET", "/api/v2/cases/projects")
    for project in result.get("data", []):
        if project.get("attributes", {}).get("key") == project_key:
            return project["id"]
    available = [p["attributes"]["key"] for p in result.get("data", []) if "attributes" in p]
    raise DatadogAPIError(
        f"Project '{project_key}' not found. Available projects: {', '.join(available)}"
    )


def datadog_create_case(
    title: str,
    project_key: str,
    case_type: str = "Standard",
    description: str = "",
    priority: str = "NOT_DEFINED",
    assignee_id: str = None,
) -> Dict[str, Any]:
    """
    Create a new Datadog case.

    Args:
        title: Case title
        project_key: Project key (e.g., "CONTENT", "MON")
        case_type: Case type name (default: "Standard")
                   Available types: "Standard", "Event Management", "Security",
                   "Change Request", "Error Tracking", "Logs Optimization Insights"
        description: Case description (optional)
        priority: Case priority - one of: "NOT_DEFINED", "P1", "P2", "P3", "P4", "P5"
        assignee_id: User UUID to assign the case to (optional)

    Returns:
        Dictionary containing the created case details

    Raises:
        DatadogAPIError: If the API request fails or project/type not found
        ValueError: If priority is not valid

    Example:
        >>> result = datadog_create_case("New issue", "CONTENT", description="Details here")
        >>> print(result['data']['attributes']['key'])
    """
    valid_priorities = ["NOT_DEFINED", "P1", "P2", "P3", "P4", "P5"]
    if priority not in valid_priorities:
        raise ValueError(
            f"Invalid priority: {priority}. Must be one of: {', '.join(valid_priorities)}"
        )

    project_id = _get_project_id(project_key)
    type_id = _get_case_type_id(case_type)

    body = {
        "data": {
            "type": "case",
            "attributes": {
                "title": title,
                "priority": priority,
                "type_id": type_id,
            },
            "relationships": {
                "project": {
                    "data": {
                        "type": "project",
                        "id": project_id
                    }
                }
            }
        }
    }

    if description:
        body["data"]["attributes"]["description"] = description

    if assignee_id:
        body["data"]["relationships"]["assignee"] = {
            "data": {
                "type": "user",
                "id": assignee_id
            }
        }

    endpoint = "/api/v2/cases"
    return _make_request("POST", endpoint, body)


def datadog_comment_case(key: str, comment: str) -> Dict[str, Any]:
    """
    Add a comment to a Datadog case.

    Args:
        key: Case key (e.g., "KEY-718")
        comment: Comment text to add to the case

    Returns:
        Dictionary containing the created comment details

    Raises:
        DatadogAPIError: If the API request fails or case not found

    Example:
        >>> result = datadog_comment_case("KEY-718", "This is a test comment")
        >>> print("Comment added successfully")
    """
    # Prepare comment request body
    body = {
        "data": {
            "type": "case",
            "attributes": {
                "comment": comment
            }
        }
    }

    # Add the comment
    endpoint = f"/api/v2/cases/{key}/comment"
    return _make_request("POST", endpoint, body)


def datadog_set_case_status(key: str, status: str) -> Dict[str, Any]:
    """
    Set the status of a Datadog case.

    Args:
        key: Case key (e.g., "KEY-718")
        status: Case status - must be one of: "IN_PROGRESS", "OPEN", "CLOSED"

    Returns:
        Dictionary containing the updated case details

    Raises:
        DatadogAPIError: If the API request fails or case not found
        ValueError: If status is not valid

    Example:
        >>> result = datadog_set_case_status("KEY-718", "IN_PROGRESS")
        >>> print("Status updated successfully")
    """
    # Validate status
    valid_statuses = ["IN_PROGRESS", "OPEN", "CLOSED"]
    if status not in valid_statuses:
        raise ValueError(
            f"Invalid status: {status}. Must be one of: {', '.join(valid_statuses)}"
        )

    # Prepare status request body
    body = {
        "data": {
            "type": "case",
            "attributes": {
                "status": status
            }
        }
    }

    # Set the status
    endpoint = f"/api/v2/cases/{key}/status"
    return _make_request("POST", endpoint, body)


def datadog_assign_case(key: str, assignee_id: str) -> Dict[str, Any]:
    """
    Assign a Datadog case to a user.

    Args:
        key: Case key (e.g., "CONTENT-1983")
        assignee_id: UUID of the user to assign (e.g., "1816ebdc-1434-11ee-b732-76f284310139")

    Returns:
        Dictionary containing the updated case details

    Raises:
        DatadogAPIError: If the API request fails or case not found
    """
    body = {
        "data": {
            "type": "case",
            "attributes": {
                "assignee_id": assignee_id
            }
        }
    }

    endpoint = f"/api/v2/cases/{key}/assign"
    return _make_request("POST", endpoint, body)


def datadog_find_user(filter: str) -> Dict[str, Any]:
    """
    Find Datadog users by email, handle, or name (substring match).

    Wraps GET /api/v2/users?filter=<filter>. Useful for resolving the
    UUID needed by datadog_assign_case from a known email.

    Args:
        filter: Filter string (email, handle, or name substring).
                Example: "pavel@vio.com"

    Returns:
        Dictionary with matched users:
        {
            "users": [
                {
                    "id": "<uuid>",
                    "email": "...",
                    "handle": "...",
                    "name": "...",
                    "status": "Active",
                    "disabled": false
                },
                ...
            ],
            "total_count": <int>
        }

    Raises:
        DatadogAPIError: If the API request fails

    Example:
        >>> result = datadog_find_user("pavel@vio.com")
        >>> uuid = result["users"][0]["id"]
    """
    params = {"filter": filter}
    query_string = urllib.parse.urlencode(params)
    endpoint = f"/api/v2/users?{query_string}"
    raw = _make_request("GET", endpoint)

    users = []
    for u in raw.get("data", []):
        attrs = u.get("attributes", {})
        users.append({
            "id": u.get("id"),
            "email": attrs.get("email"),
            "handle": attrs.get("handle"),
            "name": attrs.get("name"),
            "status": attrs.get("status"),
            "disabled": attrs.get("disabled"),
        })

    return {
        "users": users,
        "total_count": len(users),
    }


def datadog_link_cases(
    parent_key: str,
    child_key: str,
    relationship: str = "DUPLICATES"
) -> Dict[str, Any]:
    """
    Create a relationship between two Datadog cases.

    Args:
        parent_key: Parent case key (e.g., "KEY-718")
        child_key: Child case key (e.g., "KEY-792")
        relationship: Relationship type (default: "DUPLICATES")
                     Valid values: "DUPLICATES", "RELATES_TO", "BLOCKS", etc.

    Returns:
        Dictionary containing the created link details

    Raises:
        DatadogAPIError: If the API request fails or cases not found

    Example:
        >>> # Mark KEY-792 as duplicate of KEY-718
        >>> result = datadog_link_cases("KEY-718", "KEY-792", "DUPLICATES")
        >>> print("Cases linked successfully")
    """
    # First, get both cases to retrieve their internal IDs
    try:
        parent_data = datadog_get_case(parent_key)
        child_data = datadog_get_case(child_key)
    except DatadogAPIError as e:
        raise DatadogAPIError(f"Failed to retrieve case details: {e}")

    # Extract internal case IDs
    parent_id = parent_data['data']['id']
    child_id = child_data['data']['id']

    # Prepare link request body
    body = {
        "data": {
            "type": "link",
            "attributes": {
                "child_entity_id": child_id,
                "child_entity_type": "CASE",
                "parent_entity_id": parent_id,
                "parent_entity_type": "CASE",
                "relationship": relationship
            }
        }
    }

    # Create the link
    endpoint = "/api/v2/cases/link"
    return _make_request("POST", endpoint, body)


def datadog_assign_case(key: str, assignee_id: str) -> Dict[str, Any]:
    """
    Assign a Datadog case to a user.

    Args:
        key: Case key (e.g., "KEY-718")
        assignee_id: Assignee's Datadog user UUID (e.g., "ec34f974-2c51-11ee-bc35-7a3adbb5cabc")

    Returns:
        Updated case payload (includes relationships.assignee).

    Raises:
        DatadogAPIError: If the API request fails.

    Example:
        >>> datadog_assign_case("KEY-2401", "ec34f974-2c51-11ee-bc35-7a3adbb5cabc")
    """
    body = {
        "data": {
            "type": "case",
            "attributes": {
                "assignee_id": assignee_id
            }
        }
    }
    endpoint = f"/api/v2/cases/{key}/assign"
    return _make_request("POST", endpoint, body)


def datadog_unassign_case(key: str) -> Dict[str, Any]:
    """
    Remove the current assignee from a Datadog case.

    Args:
        key: Case key (e.g., "KEY-718")

    Returns:
        Updated case payload (relationships.assignee is null after this call).

    Raises:
        DatadogAPIError: If the API request fails or the case is not found.

    Example:
        >>> datadog_unassign_case("KEY-2401")
    """
    body = {
        "data": {
            "type": "case",
            "attributes": {}
        }
    }
    endpoint = f"/api/v2/cases/{key}/unassign"
    return _make_request("POST", endpoint, body)


def _clean_log_entry(log: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean a log entry to return only essential fields.

    Args:
        log: Raw log entry from Datadog API

    Returns:
        Cleaned log entry with only essential fields
    """
    attrs = log.get("attributes", {})

    # Extract essential fields
    cleaned = {
        "timestamp": attrs.get("timestamp"),
        "message": attrs.get("message", ""),
        "status": attrs.get("status"),
    }

    # Add service if available
    if "service" in attrs:
        cleaned["service"] = attrs["service"]

    # Add custom attributes (flatten nested attributes)
    custom_attrs = attrs.get("attributes", {})
    if custom_attrs:
        # Filter out internal/noisy fields
        excluded_keys = {"tags", "host", "source"}
        for key, value in custom_attrs.items():
            if key not in excluded_keys:
                cleaned[key] = value

    return cleaned


def datadog_logs_search(
    query: str,
    time_range: str = "1h",
    limit: int = 100,
    sort: str = "-timestamp"
) -> Dict[str, Any]:
    """
    Search Datadog logs with the given query.

    Args:
        query: Log search query string
               Examples:
                 - "job_id:12345" - search for specific job_id
                 - "service:my-service status:error" - filter by service and status
                 - "*" - all logs
                 - "@http.status_code:500" - search by attribute
        time_range: Time range for the search (default: "1h")
                   Supports relative formats:
                     - "1h" - last hour
                     - "1d" - last day
                     - "7d" - last 7 days
                     - "30m" - last 30 minutes
                   Or can use "now" and "now-<duration>" format internally
        limit: Maximum number of logs to return (default: 100, max: 1000)
        sort: Sort order (default: "-timestamp" for newest first)
              Use "timestamp" for oldest first

    Returns:
        Dictionary containing cleaned logs:
        {
            "logs": [
                {
                    "timestamp": "2024-01-01T00:00:00Z",
                    "message": "log message",
                    "status": "info",
                    "service": "service-name",
                    "job_id": "...",  # Custom attributes
                    ...
                }
            ],
            "count": 10,
            "has_more": false
        }

    Raises:
        DatadogAPIError: If the API request fails

    Example:
        >>> # Search for logs from a specific job in the last day
        >>> result = datadog_logs_search(
        ...     query="job_id:abc-123",
        ...     time_range="1d",
        ...     limit=50
        ... )
        >>> for log in result['logs']:
        ...     print(f"{log['timestamp']}: {log['message']}")
    """
    # Convert time_range to from/to format
    # time_range format: "1h", "1d", "30m", etc.
    to_time = "now"
    from_time = f"now-{time_range}"

    # Prepare request body
    body = {
        "filter": {
            "query": query,
            "from": from_time,
            "to": to_time
        },
        "page": {
            "limit": min(limit, 1000)  # Max 1000 per API
        },
        "sort": sort
    }

    # Make the request
    endpoint = "/api/v2/logs/events/search"
    raw_result = _make_request("POST", endpoint, body)

    # Clean up the response
    logs = raw_result.get("data", [])
    cleaned_logs = [_clean_log_entry(log) for log in logs]

    # Return simplified structure
    return {
        "logs": cleaned_logs,
        "count": len(cleaned_logs),
        "has_more": "after" in raw_result.get("meta", {}).get("page", {})
    }


def _clean_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and flatten a raw event from the Datadog Events API."""
    attrs = event.get("attributes", {})
    cleaned = {
        "id": event.get("id"),
        "title": attrs.get("attributes", {}).get("title", ""),
        "message": attrs.get("message", ""),
        "timestamp": attrs.get("timestamp"),
        "status": attrs.get("attributes", {}).get("status"),
        "priority": attrs.get("attributes", {}).get("priority"),
        "source": attrs.get("attributes", {}).get("evt", {}).get("type", ""),
        "tags": attrs.get("tags", []),
    }
    return {k: v for k, v in cleaned.items() if v is not None and v != "" and v != []}


def datadog_events_list(
    query: str = "*",
    time_range: str = "1d",
    limit: int = 100,
    sort: str = "-timestamp"
) -> Dict[str, Any]:
    """
    List Datadog events matching a query.

    Args:
        query: Event search query string (default: "*" for all events)
               Examples:
                 - "*" - all events
                 - "source:kubernetes" - events from kubernetes
                 - "status:error" - error events
                 - "tags:env:production" - events with specific tag
        time_range: Time range for the search (default: "1d")
                   Supports: "1h", "1d", "7d", "30m", etc.
        limit: Maximum number of events to return (default: 100, max: 1000)
        sort: Sort order (default: "-timestamp" for newest first)
              Use "timestamp" for oldest first

    Returns:
        Dictionary with events, count, and pagination info.

    Raises:
        DatadogAPIError: If the API request fails
    """
    to_time = "now"
    from_time = f"now-{time_range}"

    params = {
        "filter[query]": query,
        "filter[from]": from_time,
        "filter[to]": to_time,
        "page[limit]": str(min(limit, 1000)),
        "sort": sort,
    }

    query_string = urllib.parse.urlencode(params)
    endpoint = f"/api/v2/events?{query_string}"
    raw_result = _make_request("GET", endpoint)

    events = raw_result.get("data", [])
    cleaned_events = [_clean_event(e) for e in events]

    meta = raw_result.get("meta", {})
    has_more = "after" in meta.get("page", {})

    return {
        "events": cleaned_events,
        "count": len(cleaned_events),
        "has_more": has_more,
    }


def datadog_search_events(
    query: str = "*",
    time_from: str = "now-1h",
    time_to: str = "now",
    limit: int = 10,
    sort: str = "-timestamp",
    cursor: str = None,
    timezone: str = None,
) -> Dict[str, Any]:
    """
    Search Datadog events using the POST events search endpoint.

    Args:
        query: Event search query string (default: "*" for all events)
               Examples:
                 - "*" - all events
                 - "source:kubernetes" - events from kubernetes
                 - "status:error" - error events
        time_from: The minimum time for the requested events.
                   Supports date math and regular timestamps in milliseconds.
        time_to: The maximum time for the requested events.
                 Supports date math and regular timestamps in milliseconds.
        limit: Maximum number of events per page (default: 10, max: 1000)
        sort: Sort order (default: "-timestamp" for newest first)
              Use "timestamp" for oldest first
        cursor: Pagination cursor from a previous response (optional)
        timezone: Timezone for results, e.g. "Europe/Amsterdam" (optional)

    Returns:
        Dictionary with events, count, and pagination info:
        {
            "events": [...],
            "count": 10,
            "cursor": "..." or null
        }

    Raises:
        DatadogAPIError: If the API request fails
    """
    body: Dict[str, Any] = {
        "filter": {
            "from": time_from,
            "query": query,
            "to": time_to,
        },
        "page": {
            "limit": min(limit, 1000),
        },
        "sort": sort,
    }

    if cursor:
        body["page"]["cursor"] = cursor

    if timezone:
        body["options"] = {"timezone": timezone}

    endpoint = "/api/v2/events/search"
    raw_result = _make_request("POST", endpoint, body)

    events = raw_result.get("data", [])
    cleaned_events = [_clean_event(e) for e in events]

    page_meta = raw_result.get("meta", {}).get("page", {})
    next_cursor = page_meta.get("after")

    return {
        "events": cleaned_events,
        "count": len(cleaned_events),
        "cursor": next_cursor,
    }


def main():
    """
    Main function for testing the Datadog tools.
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Search:      python datadog_tools.py search [filter_query]")
        print("               (e.g., 'circuit breaker status:open')")
        print("  Create case: python datadog_tools.py create <project_key> <title> [description]")
        print("  Get case:    python datadog_tools.py get <case_key>")
        print("  Add comment: python datadog_tools.py comment <case_key> <comment_text>")
        print("  Set status:  python datadog_tools.py status <case_key> <status>")
        print("               (status: IN_PROGRESS, OPEN, or CLOSED)")
        print("  Link cases:  python datadog_tools.py link <parent_key> <child_key> [relationship]")
        print("  Assign:      python datadog_tools.py assign <case_key> <assignee_uuid>")
        print("  Unassign:    python datadog_tools.py unassign <case_key>")
        print("  Search logs: python datadog_tools.py logs <query> [time_range] [limit]")
        print("               (e.g., 'job_id:abc-123 1d 50')")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "search":
            filter_query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
            result = datadog_search_cases(filter=filter_query)
            print(json.dumps(result, indent=2))

        elif command == "create":
            if len(sys.argv) < 4:
                print("Error: Missing project_key and/or title")
                sys.exit(1)

            project_key = sys.argv[2]
            title = sys.argv[3]
            description = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""

            result = datadog_create_case(title, project_key, description=description)
            print(json.dumps(result, indent=2))

        elif command == "get":
            if len(sys.argv) < 3:
                print("Error: Missing case key")
                sys.exit(1)

            case_key = sys.argv[2]
            result = datadog_get_case(case_key)
            print(json.dumps(result, indent=2))

        elif command == "comment":
            if len(sys.argv) < 4:
                print("Error: Missing case key and/or comment text")
                sys.exit(1)

            case_key = sys.argv[2]
            comment_text = " ".join(sys.argv[3:])  # Join remaining args as comment text

            result = datadog_comment_case(case_key, comment_text)
            print(json.dumps(result, indent=2))

        elif command == "status":
            if len(sys.argv) < 4:
                print("Error: Missing case key and/or status")
                sys.exit(1)

            case_key = sys.argv[2]
            status = sys.argv[3]

            result = datadog_set_case_status(case_key, status)
            print(json.dumps(result, indent=2))

        elif command == "link":
            if len(sys.argv) < 4:
                print("Error: Missing parent_key and/or child_key")
                sys.exit(1)

            parent_key = sys.argv[2]
            child_key = sys.argv[3]
            relationship = sys.argv[4] if len(sys.argv) > 4 else "DUPLICATES"

            result = datadog_link_cases(parent_key, child_key, relationship)
            print(json.dumps(result, indent=2))

        elif command == "assign":
            if len(sys.argv) < 4:
                print("Error: Missing case key and/or assignee UUID")
                sys.exit(1)

            case_key = sys.argv[2]
            assignee_id = sys.argv[3]
            result = datadog_assign_case(case_key, assignee_id)
            print(json.dumps(result, indent=2))

        elif command == "unassign":
            if len(sys.argv) < 3:
                print("Error: Missing case key")
                sys.exit(1)

            case_key = sys.argv[2]
            result = datadog_unassign_case(case_key)
            print(json.dumps(result, indent=2))

        elif command == "logs":
            if len(sys.argv) < 3:
                print("Error: Missing query")
                sys.exit(1)

            query = sys.argv[2]
            time_range = sys.argv[3] if len(sys.argv) > 3 else "1h"
            limit = int(sys.argv[4]) if len(sys.argv) > 4 else 100

            result = datadog_logs_search(query, time_range, limit)
            print(json.dumps(result, indent=2))

        else:
            print(f"Error: Unknown command '{command}'")
            sys.exit(1)

    except DatadogAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
