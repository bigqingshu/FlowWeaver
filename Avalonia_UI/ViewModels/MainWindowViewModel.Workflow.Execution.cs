using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private const int WorkflowRunTerminalRefreshAttemptCount = 40;

    [ObservableProperty]
    private bool isStartingWorkflow;

    [ObservableProperty]
    private string? lastStartedRunId;

    [ObservableProperty]
    private string? lastStartedRunStatus;

    [RelayCommand(CanExecute = nameof(CanStartSelectedWorkflow))]
    private async Task StartSelectedWorkflowAsync()
    {
        if (SelectedWorkflow is null)
        {
            return;
        }

        if (!FlushPendingNodeConfigAutoSave())
        {
            WorkflowMessage = T("workflow.start_failed");
            WorkflowErrorMessage = WorkflowDefinitionValidationErrorMessage;
            ShowWorkflowNotification("workflow.run", UiNotificationKind.Error);
            return;
        }

        IsStartingWorkflow = true;
        WorkflowMessage = F("format.starting_workflow", SelectedWorkflow.Name);
        WorkflowErrorMessage = null;
        LastStartedRunId = null;
        LastStartedRunStatus = null;

        if (IsWorkflowDefinitionDraftDirty)
        {
            WorkflowMessage = T("workflow.saving_draft_before_run");
            if (!await EnsureWorkflowDefinitionDraftSavedForRunAsync())
            {
                WorkflowMessage = T("workflow.start_failed");
                WorkflowErrorMessage = WorkflowDefinitionValidationErrorMessage;
                ShowWorkflowNotification("workflow.run", UiNotificationKind.Error);
                IsStartingWorkflow = false;
                return;
            }
        }

        if (SelectedWorkflow is null)
        {
            WorkflowMessage = T("workflow.start_failed");
            WorkflowErrorMessage = T("definition.load_before_saving");
            ShowWorkflowNotification("workflow.run", UiNotificationKind.Error);
            IsStartingWorkflow = false;
            return;
        }

        WorkflowMessage = F("format.starting_workflow", SelectedWorkflow.Name);
        var response = await _apiClient.StartWorkflowRunAsync(
            BuildSettings(),
            SelectedWorkflow.WorkflowId,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            LastStartedRunId = response.Data.WorkflowRunId;
            LastStartedRunStatus = response.Data.Status;
            WorkflowMessage =
                F(
                    "format.started_run_with_status",
                    response.Data.WorkflowRunId,
                    response.Data.Status);
            ShowWorkflowNotification("workflow.run", UiNotificationKind.Success);
            IsStartingWorkflow = false;
            await TrackWorkflowRunUntilTerminalAsync(response.Data.WorkflowRunId);
            await SelectLatestReadableOutputNodeForRunAsync(response.Data.WorkflowRunId);
            if (CanRefreshSelectedWorkflowNodeDataPreview())
            {
                await RefreshSelectedWorkflowNodeDataPreviewAsync();
            }

            return;
        }

        WorkflowMessage = T("workflow.start_failed");
        WorkflowErrorMessage = DescribeError(response);
        ShowWorkflowNotification("workflow.run", UiNotificationKind.Error);
        IsStartingWorkflow = false;
    }

    private async Task TrackWorkflowRunUntilTerminalAsync(string workflowRunId)
    {
        for (var attempt = 0; attempt < WorkflowRunTerminalRefreshAttemptCount; attempt++)
        {
            await LoadRunsAsync(workflowRunId);
            if (SelectedRun is not null && IsTerminalRunStatus(SelectedRun.Status))
            {
                return;
            }

            if (attempt + 1 < WorkflowRunTerminalRefreshAttemptCount)
            {
                await _dataPreviewRunRefreshDelay(_shutdown.Token);
            }
        }
    }
}
