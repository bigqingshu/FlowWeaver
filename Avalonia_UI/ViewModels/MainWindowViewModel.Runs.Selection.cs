using System;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnSelectedRunChanged(
        WorkflowRunListItemViewModel? oldValue,
        WorkflowRunListItemViewModel? newValue)
    {
        var runChanged = !string.Equals(
            oldValue?.WorkflowRunId,
            newValue?.WorkflowRunId,
            StringComparison.Ordinal);
        if (runChanged)
        {
            _ = RunLoopMonitor.SelectRunAsync(
                BuildSettings(),
                newValue?.WorkflowRunId);
            nodeRunsLoadVersion++;
            tableRefsLoadVersion++;
            IsLoadingNodeRuns = false;
            IsLoadingTableRefs = false;
            NodeRuns.Clear();
            TableRefs.Clear();
            NodeRunMessage = newValue is null
                ? T("status.select_run_node_status")
                : F("format.selected_run_refresh_nodes", newValue.WorkflowRunId);
            NodeRunErrorMessage = null;
            TableRefMessage = newValue is null
                ? T("status.select_run_table_refs")
                : F("format.selected_run_refresh_table_refs", newValue.WorkflowRunId);
            TableRefErrorMessage = null;
            ResetDataPreviewSelectionState();
            ResetDataPreviewWorkbenchState();
        }
        else
        {
            RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        }

        NotifyEngineActionStateChanged();
        OnPropertyChanged(nameof(HasSelectedRunRuntimeOptionsSummary));
        OnPropertyChanged(nameof(SelectedRunRuntimeOptionsSummaryText));
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }
}
