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


def datadog_get_case(key: str) -> Dict[str, Any]:
    """
    Get details of a Datadog case by its key.

    Args:
        key: Case key (e.g., "CONTENT-718")

    Returns:
        Dictionary containing case details with structure:
        {
            "data": {
                "id": "case_uuid",
                "type": "case",
                "attributes": {
                    "key": "CONTENT-718",
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
        >>> case_data = datadog_get_case("CONTENT-718")
        >>> print(case_data['data']['attributes']['title'])
    """
    endpoint = f"/api/v2/cases/{key}"
    return _make_request("GET", endpoint)


def datadog_comment_case(key: str, comment: str) -> Dict[str, Any]:
    """
    Add a comment to a Datadog case.

    Args:
        key: Case key (e.g., "CONTENT-718")
        comment: Comment text to add to the case

    Returns:
        Dictionary containing the created comment details

    Raises:
        DatadogAPIError: If the API request fails or case not found

    Example:
        >>> result = datadog_comment_case("CONTENT-718", "This is a test comment")
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
        key: Case key (e.g., "CONTENT-718")
        status: Case status - must be one of: "IN_PROGRESS", "OPEN", "CLOSED"

    Returns:
        Dictionary containing the updated case details

    Raises:
        DatadogAPIError: If the API request fails or case not found
        ValueError: If status is not valid

    Example:
        >>> result = datadog_set_case_status("CONTENT-718", "IN_PROGRESS")
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


def datadog_link_cases(
    parent_key: str,
    child_key: str,
    relationship: str = "DUPLICATES"
) -> Dict[str, Any]:
    """
    Create a relationship between two Datadog cases.

    Args:
        parent_key: Parent case key (e.g., "CONTENT-718")
        child_key: Child case key (e.g., "CONTENT-792")
        relationship: Relationship type (default: "DUPLICATES")
                     Valid values: "DUPLICATES", "RELATES_TO", "BLOCKS", etc.

    Returns:
        Dictionary containing the created link details

    Raises:
        DatadogAPIError: If the API request fails or cases not found

    Example:
        >>> # Mark CONTENT-792 as duplicate of CONTENT-718
        >>> result = datadog_link_cases("CONTENT-718", "CONTENT-792", "DUPLICATES")
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


def main():
    """
    Main function for testing the Datadog tools.
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Get case:    python datadog_tools.py get <case_key>")
        print("  Add comment: python datadog_tools.py comment <case_key> <comment_text>")
        print("  Set status:  python datadog_tools.py status <case_key> <status>")
        print("               (status: IN_PROGRESS, OPEN, or CLOSED)")
        print("  Link cases:  python datadog_tools.py link <parent_key> <child_key> [relationship]")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "get":
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

        else:
            print(f"Error: Unknown command '{command}'")
            sys.exit(1)

    except DatadogAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
