namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string? LocalizeWorkflowDefinitionDraftWarning(string? warning)
    {
        if (string.IsNullOrWhiteSpace(warning))
        {
            return warning;
        }

        return warning switch
        {
            "WORKFLOW_DRAFT_JSON_INVALID" => T("definition.warning.workflow_draft_json_invalid"),
            "RUNTIME_OPTIONS_JSON_INVALID" => T("definition.warning.runtime_options_json_invalid"),
            "WORKFLOW_DRAFT_ROOT_NOT_OBJECT" => T("definition.warning.workflow_draft_root_not_object"),
            "WORKFLOW_DRAFT_NODES_MISSING" => T("definition.warning.workflow_draft_nodes_missing"),
            "WORKFLOW_DRAFT_CONNECTIONS_MISSING" => T("definition.warning.workflow_draft_connections_missing"),
            "RUNTIME_OPTIONS_NOT_OBJECT" => T("definition.warning.runtime_options_not_object"),
            "NODE_INSTANCE_ID_REQUIRED" => T("definition.warning.node_instance_id_required"),
            "NODE_TYPE_REQUIRED" => T("definition.warning.node_type_required"),
            "NODE_VERSION_REQUIRED" => T("definition.warning.node_version_required"),
            "CONFIG_UNSUPPORTED" => T("definition.warning.node_config_unsupported"),
            "NODE_ALREADY_EXISTS" => T("definition.warning.node_already_exists"),
            "NODE_NOT_FOUND" => T("definition.warning.node_not_found"),
            "INSERT_AFTER_NODE_NOT_FOUND" => T("definition.warning.insert_after_node_not_found"),
            "NODE_MOVE_OUT_OF_RANGE" => T("definition.warning.node_move_out_of_range"),
            "NODE_HAS_CONNECTIONS" => T("definition.warning.node_has_connections"),
            "CONNECTION_ID_REQUIRED" => T("definition.warning.connection_id_required"),
            "CONNECTION_ALREADY_EXISTS" => T("definition.warning.connection_already_exists"),
            "CONNECTION_NOT_FOUND" => T("definition.warning.connection_not_found"),
            "CONNECTION_UNSUPPORTED" => T("definition.warning.connection_unsupported"),
            "SOURCE_NODE_ID_REQUIRED" => T("definition.warning.source_node_id_required"),
            "SOURCE_NODE_NOT_FOUND" => T("definition.warning.source_node_not_found"),
            "SOURCE_PORT_REQUIRED" => T("definition.warning.source_port_required"),
            "TARGET_NODE_ID_REQUIRED" => T("definition.warning.target_node_id_required"),
            "TARGET_NODE_NOT_FOUND" => T("definition.warning.target_node_not_found"),
            "TARGET_PORT_REQUIRED" => T("definition.warning.target_port_required"),
            "LINEAR_CHAIN_DISCONNECTED" => T("definition.warning.linear_chain_disconnected"),
            "LINEAR_CHAIN_BRANCHING" => T("definition.warning.linear_chain_branching"),
            "LINEAR_CHAIN_MERGING" => T("definition.warning.linear_chain_merging"),
            "LINEAR_CHAIN_NOT_SINGLE_CHAIN" => T("definition.warning.linear_chain_not_single_chain"),
            "LINEAR_CHAIN_CYCLE" => T("definition.warning.linear_chain_cycle"),
            _ => warning,
        };
    }
}
