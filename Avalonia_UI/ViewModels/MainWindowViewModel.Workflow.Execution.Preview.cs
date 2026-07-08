using System;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanPreviewSelectedWorkflowNode))]
    private async Task PreviewSelectedWorkflowNodeAsync()
    {
        if (SelectedWorkflow is null || SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var targetNodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        IsStartingWorkflow = true;
        WorkflowMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        WorkflowErrorMessage = null;
        DataPreviewMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        DataPreviewErrorMessage = null;
        LastStartedRunId = null;
        LastStartedRunStatus = null;

        if (IsWorkflowDefinitionDraftDirty)
        {
            WorkflowMessage = T("workflow.saving_draft_before_preview");
            DataPreviewMessage = T("workflow.saving_draft_before_preview");
            if (!await EnsureWorkflowDefinitionDraftSavedForRunAsync())
            {
                WorkflowMessage = T("workflow.start_failed");
                WorkflowErrorMessage = WorkflowDefinitionValidationErrorMessage;
                DataPreviewMessage = T("data_preview.preview_failed");
                DataPreviewErrorMessage = WorkflowDefinitionValidationErrorMessage;
                ShowWorkflowNotification("workflow.preview", UiNotificationKind.Error);
                ShowDataPreviewNotification(UiNotificationKind.Error);
                IsStartingWorkflow = false;
                return;
            }

            SelectWorkflowDefinitionDraftNode(targetNodeInstanceId);
        }

        if (SelectedWorkflow is null ||
            SelectedWorkflowDefinitionNode is null ||
            !string.Equals(
                SelectedWorkflowDefinitionNode.NodeInstanceId,
                targetNodeInstanceId,
                StringComparison.Ordinal))
        {
            WorkflowMessage = T("workflow.start_failed");
            WorkflowErrorMessage = T("action.disabled.workflow_node_missing");
            DataPreviewMessage = T("data_preview.preview_failed");
            DataPreviewErrorMessage = T("action.disabled.workflow_node_missing");
            ShowWorkflowNotification("workflow.preview", UiNotificationKind.Error);
            ShowDataPreviewNotification(UiNotificationKind.Error);
            IsStartingWorkflow = false;
            return;
        }

        WorkflowMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        DataPreviewMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        var response = await _apiClient.StartWorkflowRunAsync(
            BuildSettings(),
            SelectedWorkflow.WorkflowId,
            "preview_to_node",
            targetNodeInstanceId,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            LastStartedRunId = response.Data.WorkflowRunId;
            LastStartedRunStatus = response.Data.Status;
            WorkflowMessage =
                F(
                    "format.started_preview_run_with_status",
                    response.Data.WorkflowRunId,
                    response.Data.Status,
                    targetNodeInstanceId);
            ShowWorkflowNotification("workflow.preview", UiNotificationKind.Success);
            IsStartingWorkflow = false;
            await RefreshSelectedWorkflowNodeDataPreviewAfterRunStartAsync(response.Data.WorkflowRunId);

            return;
        }

        WorkflowMessage = T("workflow.start_failed");
        WorkflowErrorMessage = DescribeError(response);
        DataPreviewMessage = T("data_preview.preview_failed");
        DataPreviewErrorMessage = DescribeError(response);
        ShowWorkflowNotification("workflow.preview", UiNotificationKind.Error);
        ShowDataPreviewNotification(UiNotificationKind.Error);
        IsStartingWorkflow = false;
    }
}
