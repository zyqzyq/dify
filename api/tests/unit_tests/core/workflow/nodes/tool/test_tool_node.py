from __future__ import annotations

import sys
import types
from collections.abc import Generator
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from core.file import File, FileTransferMethod, FileType
from core.model_runtime.entities.llm_entities import LLMUsage
from core.tools.entities.common_entities import I18nObject
from core.tools.entities.tool_entities import ToolInvokeMessage, ToolParameter, ToolProviderType
from core.tools.utils.message_transformer import ToolFileMessageTransformer
from core.variables.segments import ArrayFileSegment
from core.workflow.entities import GraphInitParams
from core.workflow.node_events import StreamChunkEvent, StreamCompletedEvent
from core.workflow.nodes.tool.entities import ToolNodeData
from core.workflow.runtime import GraphRuntimeState, VariablePool
from core.workflow.system_variable import SystemVariable

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from core.workflow.nodes.tool.tool_node import ToolNode


@pytest.fixture
def tool_node(monkeypatch) -> ToolNode:
    module_name = "core.ops.ops_trace_manager"
    if module_name not in sys.modules:
        ops_stub = types.ModuleType(module_name)
        ops_stub.TraceQueueManager = object  # pragma: no cover - stub attribute
        ops_stub.TraceTask = object  # pragma: no cover - stub attribute
        monkeypatch.setitem(sys.modules, module_name, ops_stub)

    from core.workflow.nodes.tool.tool_node import ToolNode

    graph_config: dict[str, Any] = {
        "nodes": [
            {
                "id": "tool-node",
                "data": {
                    "type": "tool",
                    "title": "Tool",
                    "desc": "",
                    "provider_id": "provider",
                    "provider_type": "builtin",
                    "provider_name": "provider",
                    "tool_name": "tool",
                    "tool_label": "tool",
                    "tool_configurations": {},
                    "tool_parameters": {},
                },
            }
        ],
        "edges": [],
    }

    init_params = GraphInitParams(
        tenant_id="tenant-id",
        app_id="app-id",
        workflow_id="workflow-id",
        graph_config=graph_config,
        user_id="user-id",
        user_from="account",
        invoke_from="debugger",
        call_depth=0,
    )

    variable_pool = VariablePool(system_variables=SystemVariable(user_id="user-id"))
    graph_runtime_state = GraphRuntimeState(variable_pool=variable_pool, start_at=0.0)

    config = graph_config["nodes"][0]
    node = ToolNode(
        id="node-instance",
        config=config,
        graph_init_params=init_params,
        graph_runtime_state=graph_runtime_state,
    )
    return node


def _collect_events(generator: Generator) -> tuple[list[Any], LLMUsage]:
    events: list[Any] = []
    try:
        while True:
            events.append(next(generator))
    except StopIteration as stop:
        return events, stop.value


def _run_transform(tool_node: ToolNode, message: ToolInvokeMessage) -> tuple[list[Any], LLMUsage]:
    def _identity_transform(messages, *_args, **_kwargs):
        return messages

    tool_runtime = MagicMock()
    with patch.object(ToolFileMessageTransformer, "transform_tool_invoke_messages", side_effect=_identity_transform):
        generator = tool_node._transform_message(
            messages=iter([message]),
            tool_info={"provider_type": "builtin", "provider_id": "provider"},
            parameters_for_log={},
            user_id="user-id",
            tenant_id="tenant-id",
            node_id=tool_node._node_id,
            tool_runtime=tool_runtime,
        )
        return _collect_events(generator)


def _tool_parameter(name: str, parameter_type: ToolParameter.ToolParameterType) -> ToolParameter:
    return ToolParameter(
        name=name,
        label=I18nObject(en_US=name, zh_Hans=name),
        type=parameter_type,
        form=ToolParameter.ToolParameterForm.LLM,
        required=False,
    )


def _tool_node_data(tool_parameters: dict[str, dict[str, Any]]) -> ToolNodeData:
    return ToolNodeData.model_validate(
        {
            "type": "tool",
            "title": "Tool",
            "desc": "",
            "provider_id": "provider",
            "provider_type": ToolProviderType.PLUGIN,
            "provider_name": "provider",
            "tool_name": "tool",
            "tool_label": "tool",
            "tool_configurations": {},
            "tool_parameters": tool_parameters,
        }
    )


def test_generate_parameters_preserves_constant_list_and_dict(tool_node: ToolNode):
    variable_pool = VariablePool(system_variables=SystemVariable(user_id="user-id"))
    node_data = _tool_node_data(
        {
            "multi_select": {"type": "constant", "value": ["123"]},
            "date_range": {"type": "constant", "value": {"start": "2026-06-16", "end": "2026-06-17"}},
        }
    )
    tool_parameters = [
        _tool_parameter("multi_select", ToolParameter.ToolParameterType.SELECT),
        _tool_parameter("date_range", ToolParameter.ToolParameterType.DATE_PICKER),
    ]

    result = tool_node._generate_parameters(
        tool_parameters=tool_parameters,
        variable_pool=variable_pool,
        node_data=node_data,
    )

    assert result == {
        "multi_select": ["123"],
        "date_range": {"start": "2026-06-16", "end": "2026-06-17"},
    }


def test_link_messages_with_file_populate_files_output(tool_node: ToolNode):
    file_obj = File(
        tenant_id="tenant-id",
        type=FileType.DOCUMENT,
        transfer_method=FileTransferMethod.TOOL_FILE,
        related_id="file-id",
        filename="demo.pdf",
        extension=".pdf",
        mime_type="application/pdf",
        size=123,
        storage_key="file-key",
    )
    message = ToolInvokeMessage(
        type=ToolInvokeMessage.MessageType.LINK,
        message=ToolInvokeMessage.TextMessage(text="/files/tools/file-id.pdf"),
        meta={"file": file_obj},
    )

    events, usage = _run_transform(tool_node, message)

    assert isinstance(usage, LLMUsage)

    chunk_events = [event for event in events if isinstance(event, StreamChunkEvent)]
    assert chunk_events
    assert chunk_events[0].chunk == "File: /files/tools/file-id.pdf\n"

    completed_events = [event for event in events if isinstance(event, StreamCompletedEvent)]
    assert len(completed_events) == 1
    outputs = completed_events[0].node_run_result.outputs
    assert outputs["text"] == "File: /files/tools/file-id.pdf\n"

    files_segment = outputs["files"]
    assert isinstance(files_segment, ArrayFileSegment)
    assert files_segment.value == [file_obj]


def test_plain_link_messages_remain_links(tool_node: ToolNode):
    message = ToolInvokeMessage(
        type=ToolInvokeMessage.MessageType.LINK,
        message=ToolInvokeMessage.TextMessage(text="https://dify.ai"),
        meta=None,
    )

    events, _ = _run_transform(tool_node, message)

    chunk_events = [event for event in events if isinstance(event, StreamChunkEvent)]
    assert chunk_events
    assert chunk_events[0].chunk == "Link: https://dify.ai\n"

    completed_events = [event for event in events if isinstance(event, StreamCompletedEvent)]
    assert len(completed_events) == 1
    files_segment = completed_events[0].node_run_result.outputs["files"]
    assert isinstance(files_segment, ArrayFileSegment)
    assert files_segment.value == []
