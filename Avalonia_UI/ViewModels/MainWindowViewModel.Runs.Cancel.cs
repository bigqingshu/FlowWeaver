using System;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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

    private bool CanCancelSelectedRunCore()
    {
        return CanUseEngineActions
            && SelectedRun is not null
            && IsCancelableRunStatus(SelectedRun.Status)
            && !IsRunBusy;
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
}
