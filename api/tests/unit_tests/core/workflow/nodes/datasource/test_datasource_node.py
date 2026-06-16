from __future__ import annotations

from typing import Any

from core.datasource.entities.datasource_entities import DatasourceParameter
from core.tools.entities.common_entities import I18nObject
from core.workflow.entities import GraphInitParams
from core.workflow.nodes.datasource.datasource_node import DatasourceNode
from core.workflow.nodes.datasource.entities import DatasourceNodeData
from core.workflow.runtime import GraphRuntimeState, VariablePool
from core.workflow.system_variable import SystemVariable


def _datasource_parameter(
    name: str,
    parameter_type: DatasourceParameter.DatasourceParameterType,
) -> DatasourceParameter:
    return DatasourceParameter(
        name=name,
        label=I18nObject(en_US=name, zh_Hans=name),
        description=I18nObject(en_US=name, zh_Hans=name),
        type=parameter_type,
        required=False,
    )


def _datasource_node_data(datasource_parameters: dict[str, dict[str, Any]]) -> DatasourceNodeData:
    return DatasourceNodeData.model_validate(
        {
            "type": "datasource",
            "title": "Datasource",
            "desc": "",
            "plugin_id": "plugin",
            "provider_name": "provider",
            "provider_type": "online_document",
            "datasource_name": "datasource",
            "datasource_parameters": datasource_parameters,
        }
    )


def _datasource_node() -> DatasourceNode:
    graph_config: dict[str, Any] = {
        "nodes": [
            {
                "id": "datasource-node",
                "data": {
                    "type": "datasource",
                    "title": "Datasource",
                    "desc": "",
                    "plugin_id": "plugin",
                    "provider_name": "provider",
                    "provider_type": "online_document",
                    "datasource_name": "datasource",
                    "datasource_parameters": {},
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

    return DatasourceNode(
        id="node-instance",
        config=graph_config["nodes"][0],
        graph_init_params=init_params,
        graph_runtime_state=graph_runtime_state,
    )


def test_generate_parameters_preserves_constant_list_and_dict():
    node = _datasource_node()
    variable_pool = VariablePool(system_variables=SystemVariable(user_id="user-id"))
    node_data = _datasource_node_data(
        {
            "multi_select": {"type": "constant", "value": ["123"]},
            "metadata": {"type": "constant", "value": {"page_id": "page-1"}},
        }
    )
    datasource_parameters = [
        _datasource_parameter("multi_select", DatasourceParameter.DatasourceParameterType.SELECT),
        _datasource_parameter("metadata", DatasourceParameter.DatasourceParameterType.STRING),
    ]

    result = node._generate_parameters(
        datasource_parameters=datasource_parameters,
        variable_pool=variable_pool,
        node_data=node_data,
    )

    assert result == {
        "multi_select": ["123"],
        "metadata": {"page_id": "page-1"},
    }
