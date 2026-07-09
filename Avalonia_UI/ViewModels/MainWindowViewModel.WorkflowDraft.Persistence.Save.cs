using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task<bool> TrySaveWorkflowDefinitionDraftAsync()
    {
        if (WorkflowDefinitionDetail is null)
        {
            RejectWorkflowDefinitionSaveWithoutDetail();
            return false;
        }

        if (!TryReadWorkflowDefinitionDraftJsonForSave(out var definition))
        {
            return false;
        }

        IsSavingWorkflowDefinitionDraft = true;
        WorkflowDefinitionValidationMessage = T("definition.saving_draft");
        WorkflowDefinitionValidationErrorMessage = null;

        try
        {
            var saved = await _apiClient.UpdateWorkflowAsync(
                BuildSettings(),
                WorkflowDefinitionDetail.WorkflowId,
                WorkflowDefinitionDetail.Name,
                definition,
                WorkflowDefinitionDetail.RevisionId,
                _shutdown.Token);

            if (saved.Ok && saved.Data is not null)
            {
                WorkflowDefinitionValidationMessage =
                    F("format.saved_workflow", saved.Data.Name, saved.Data.Version);
                ShowWorkflowDefinitionNotification(
                    "workflow.definition.save",
                    UiNotificationKind.Success);
                IsWorkflowDefinitionDraftDirty = false;
                HasWorkflowDefinitionRevisionConflict = false;
                await RefreshWorkflowsSelectingAsync(saved.Data.WorkflowId);
                await LoadSelectedWorkflowDefinitionAsync();
                return true;
            }

            if (saved.Error?.ErrorCode == "WORKFLOW_REVISION_CONFLICT")
            {
                HasWorkflowDefinitionRevisionConflict = true;
                WorkflowDefinitionValidationMessage = T("definition.save_failed");
                WorkflowDefinitionValidationErrorMessage = T("definition.revision_conflict");
                ShowWorkflowDefinitionNotification(
                    "workflow.definition.save",
                    UiNotificationKind.Error);
                return false;
            }

            WorkflowDefinitionValidationMessage = T("definition.save_failed");
            WorkflowDefinitionValidationErrorMessage = DescribeError(saved);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.save",
                UiNotificationKind.Error);
            return false;
        }
        finally
        {
            IsSavingWorkflowDefinitionDraft = false;
        }
    }

    private async Task<bool> EnsureWorkflowDefinitionDraftSavedForRunAsync()
    {
        return !IsWorkflowDefinitionDraftDirty ||
            await TrySaveWorkflowDefinitionDraftAsync();
    }
}
