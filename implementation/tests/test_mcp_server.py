import json

import pytest
from fastmcp import Client

from implementation import mcp_server
from implementation.init_db import create_database


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_mcp_tools_and_resources_are_discoverable():
    create_database(reset=True)

    async with Client(mcp_server.mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        resource_templates = await client.list_resource_templates()

        assert {tool.name for tool in tools} == {"search", "insert", "aggregate"}
        assert {str(resource.uri) for resource in resources} == {"schema://database"}
        assert {template.uriTemplate for template in resource_templates} == {"schema://table/{table_name}"}


@pytest.mark.anyio
async def test_mcp_search_and_schema_resource_work():
    create_database(reset=True)

    async with Client(mcp_server.mcp) as client:
        search_result = await client.call_tool(
            "search",
            {
                "table": "students",
                "filters": {"cohort": "A1"},
                "columns": ["name", "gpa"],
                "order_by": "gpa",
                "descending": True,
            },
        )
        schema_contents = await client.read_resource("schema://table/students")

    assert search_result.data["count"] == 2
    assert search_result.data["rows"][0]["name"] == "Nguyen Minh Anh"

    schema = json.loads(schema_contents[0].text)
    assert schema["table"] == "students"
    assert {column["name"] for column in schema["columns"]} >= {"id", "name", "cohort", "email", "gpa"}
