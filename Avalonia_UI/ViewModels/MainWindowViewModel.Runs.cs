using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int nodeRunsLoadVersion;

    [ObservableProperty]
    private bool isLoadingRuns;

    [ObservableProperty]
    private bool isCancellingRun;

    [ObservableProperty]
    private WorkflowRunListItemViewModel? selectedRun;

    [ObservableProperty]
    private string runMessage = "No runs loaded.";

    [ObservableProperty]
    private string? runErrorMessage;

    [ObservableProperty]
    private bool isLoadingNodeRuns;

    [ObservableProperty]
    private string nodeRunMessage = "Select a run to load node status.";

    [ObservableProperty]
    private string? nodeRunErrorMessage;

    public ObservableCollection<WorkflowRunListItemViewModel> Runs { get; } = new();

    public ObservableCollection<NodeRunListItemViewModel> NodeRuns { get; } = new();

    public bool IsRunBusy => IsLoadingRuns || IsCancellingRun;

    public bool HasRunError => !string.IsNullOrWhiteSpace(RunErrorMessage);

    public bool IsNodeRunBusy => IsLoadingNodeRuns;

    public bool HasNodeRunError => !string.IsNullOrWhiteSpace(NodeRunErrorMessage);

    public bool CanUseCancelSelectedRunAction => CanCancelSelectedRunCore();

    public string? CancelSelectedRunDisabledReasonText
    {
        get
        {
            if (IsRunBusy)
            {
                return T("action.disabled.busy");
            }

            if (!CanUseEngineActions)
            {
                return T("action.disabled.engine_not_connected");
            }

            if (SelectedRun is null)
            {
                return T("action.disabled.no_run_selected");
            }

            if (string.IsNullOrWhiteSpace(SelectedRun.Status) || SelectedRun.Status == "UNKNOWN")
            {
                return T("action.disabled.run_status_unknown");
            }

            if (IsTerminalRunStatus(SelectedRun.Status))
            {
                return T("action.disabled.run_terminal");
            }

            if (!IsCancelableRunStatus(SelectedRun.Status))
            {
                return T("action.disabled.run_not_running");
            }

            return null;
        }
    }

    private bool CanRefreshRuns()
    {
        return CanUseEngineActions && !IsRunBusy;
    }

    private bool CanCancelSelectedRunCore()
    {
        return CanUseEngineActions
            && SelectedRun is not null
            && IsCancelableRunStatus(SelectedRun.Status)
            && !IsRunBusy;
    }

    private bool CanRefreshNodeRuns()
    {
        return CanUseEngineActions && SelectedRun is not null && !IsNodeRunBusy;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshRuns))]
    private Task RefreshRunsAsync()
    {
        return LoadRunsAsync();
    }

    [RelayCommand(CanExecute = nameof(CanCancelSelectedRunCore))]
    private async Task CancelSelectedRunAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var workflowRunId = SelectedRun.WorkflowRunId;
        IsCancellingRun = true;
        RunMessage = F("format.cancelling_run", workflowRunId);
        RunErrorMessage = null;

        var response = await _apiClient.CancelRunAsync(
            BuildSettings(),
            workflowRunId,
            _shutdown.Token);

        IsCancellingRun = false;

        if (response.Ok)
        {
            var processStatus = response.Data?.Status;
            var cancelMessage = string.IsNullOrWhiteSpace(processStatus)
                ? F("format.cancel_requested", workflowRunId)
                : F("format.cancel_requested_with_status", workflowRunId, processStatus);
            await LoadRunsAsync(workflowRunId);
            if (!HasRunError)
            {
                RunMessage = cancelMessage;
            }

            return;
        }

        RunMessage = T("runs.cancel_failed");
        RunErrorMessage = DescribeError(response);
    }

    [RelayCommand(CanExecute = nameof(CanRefreshNodeRuns))]
    private async Task RefreshNodeRunsAsync()
    {
        await LoadNodeRunsForSelectedRunAsync();
    }

    private async Task LoadNodeRunsForSelectedRunAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestVersion = ++nodeRunsLoadVersion;
        IsLoadingNodeRuns = true;
        NodeRunMessage = F("format.loading_nodes_for", requestedRunId);
        NodeRunErrorMessage = null;

        try
        {
            var response = await _apiClient.ListNodeRunsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (
                SelectedRun?.WorkflowRunId != requestedRunId
                || requestVersion != nodeRunsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                NodeRuns.Clear();
                foreach (var nodeRun in response.Data)
                {
                    NodeRuns.Add(new NodeRunListItemViewModel(nodeRun, DisplayTextFormatter));
                }

                NodeRunMessage = F("format.loaded_node_runs", NodeRuns.Count);
                return;
            }

            NodeRunMessage = T("node_runs.refresh_failed");
            NodeRunErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == nodeRunsLoadVersion)
            {
                IsLoadingNodeRuns = false;
            }
        }
    }

    private async Task LoadRunsAsync(string? selectWorkflowRunId = null)
    {
        IsLoadingRuns = true;
        RunMessage = SelectedWorkflow is null
            ? T("runs.loading")
            : F("format.loading_runs_for", SelectedWorkflow.Name);
        RunErrorMessage = null;

        var workflowId = SelectedWorkflow?.WorkflowId;
        var response = await _apiClient.ListRunsAsync(
            BuildSettings(),
            workflowId,
            cancellationToken: _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            var previousRunId = selectWorkflowRunId ?? SelectedRun?.WorkflowRunId;
            Runs.Clear();
            foreach (var run in response.Data)
            {
                Runs.Add(new WorkflowRunListItemViewModel(run));
            }

            SelectedRun = Runs.FirstOrDefault(run => run.WorkflowRunId == previousRunId)
                ?? Runs.FirstOrDefault();
            RunMessage = workflowId is null
                ? F("format.loaded_runs", Runs.Count)
                : F("format.loaded_runs_for", Runs.Count, SelectedWorkflow?.Name);
            IsLoadingRuns = false;
            return;
        }

        RunMessage = T("runs.refresh_failed");
        RunErrorMessage = DescribeError(response);
        IsLoadingRuns = false;
    }

    partial void OnIsLoadingRunsChanged(bool value)
    {
        NotifyRunCommandStateChanged();
    }

    partial void OnIsCancellingRunChanged(bool value)
    {
        NotifyRunCommandStateChanged();
    }

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

    partial void OnRunErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRunError));
    }

    partial void OnIsLoadingNodeRunsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsNodeRunBusy));
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
    }

    partial void OnNodeRunErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasNodeRunError));
    }

    private void NotifyRunCommandStateChanged()
    {
        OnPropertyChanged(nameof(IsRunBusy));
        NotifyEngineActionStateChanged();
        RefreshRunsCommand.NotifyCanExecuteChanged();
    }

    private static bool IsCancelableRunStatus(string? status)
    {
        return status == "RUNNING";
    }

    private static bool IsTerminalRunStatus(string? status)
    {
        return status is "SUCCEEDED" or "FAILED" or "CANCELLED" or "ABORTED";
    }
}
