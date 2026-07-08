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

    partial void OnRunErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRunError));
    }
}
