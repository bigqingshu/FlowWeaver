using System;
using System.Collections.Generic;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private Dictionary<string, string> CaptureDefaultMessageSnapshot()
    {
        return new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["status.disconnected"] = T("status.disconnected"),
            ["status.event_stream_disconnected"] = T("status.event_stream_disconnected"),
            ["workflow.default_name"] = T("workflow.default_name"),
            ["status.no_workflows_loaded"] = T("status.no_workflows_loaded"),
            ["status.select_workflow_definition"] = T("status.select_workflow_definition"),
            ["status.no_node_definitions_loaded"] = T("status.no_node_definitions_loaded"),
            ["status.load_definition_to_edit"] = T("status.load_definition_to_edit"),
            ["status.no_runs_loaded"] = T("status.no_runs_loaded"),
            ["status.select_run_node_status"] = T("status.select_run_node_status"),
            ["status.no_runtime_events_loaded"] = T("status.no_runtime_events_loaded"),
            ["status.select_run_table_refs"] = T("status.select_run_table_refs"),
            ["status.select_run_and_workflow_node_data_preview"] =
                T("status.select_run_and_workflow_node_data_preview"),
            ["data_preview.workbench_select_table"] = T("data_preview.workbench_select_table"),
            ["status.no_shared_publications_loaded"] = T("status.no_shared_publications_loaded"),
            ["status.select_share_versions"] = T("status.select_share_versions"),
        };
    }

    private static bool ShouldRefreshDefault(
        string currentValue,
        IReadOnlyDictionary<string, string>? previousDefaults,
        string key)
    {
        return previousDefaults is null
            || (previousDefaults.TryGetValue(key, out var previousValue)
                && string.Equals(currentValue, previousValue, StringComparison.Ordinal));
    }
}
