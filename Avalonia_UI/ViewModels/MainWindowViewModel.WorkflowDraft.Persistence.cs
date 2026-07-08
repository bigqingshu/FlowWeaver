using System.Text.Json;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRestoreWorkflowDefinitionDraft()
    {
        return HasWorkflowDefinitionDraft
            && IsWorkflowDefinitionDraftDirty
            && !IsWorkflowDefinitionDraftBusy;
    }

    private bool CanSaveWorkflowDefinitionDraft()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && IsWorkflowDefinitionDraftDirty
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }

    [RelayCommand(CanExecute = nameof(CanRestoreWorkflowDefinitionDraft))]
    private void RestoreWorkflowDefinitionDraft()
    {
        if (!CanRestoreWorkflowDefinitionDraft())
        {
            return;
        }

        var selectedNodeId = SelectedWorkflowDefinitionNode?.NodeInstanceId;
        WorkflowDefinitionDraftJson = originalWorkflowDefinitionJson;
        if (!string.IsNullOrWhiteSpace(selectedNodeId))
        {
            SelectWorkflowDefinitionDraftNode(selectedNodeId);
        }

        WorkflowDefinitionValidationMessage = T("definition.draft_restored");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.restore",
            UiNotificationKind.Success);
    }

    [RelayCommand(CanExecute = nameof(CanSaveWorkflowDefinitionDraft))]
    private async Task SaveWorkflowDefinitionDraftAsync()
    {
        await TrySaveWorkflowDefinitionDraftAsync();
    }

    private async Task<bool> TrySaveWorkflowDefinitionDraftAsync()
    {
        if (WorkflowDefinitionDetail is null)
        {
            WorkflowDefinitionValidationMessage = T("definition.save_rejected");
            WorkflowDefinitionValidationErrorMessage = T("definition.load_before_saving");
            ShowWorkflowDefinitionNotification(
                "workflow.definition.save",
                UiNotificationKind.Error);
            return false;
        }

        JsonElement definition;
        try
        {
            using var parsed = JsonDocument.Parse(WorkflowDefinitionDraftJson);
            definition = parsed.RootElement.Clone();
        }
        catch (JsonException ex)
        {
            WorkflowDefinitionValidationMessage = T("definition.draft_json_invalid");
            WorkflowDefinitionValidationErrorMessage = ex.Message;
            ShowWorkflowDefinitionNotification(
                "workflow.definition.save",
                UiNotificationKind.Error);
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

    partial void OnIsSavingWorkflowDefinitionDraftChanged(bool value)
    {
        OnPropertyChanged(nameof(IsWorkflowDefinitionDraftBusy));
        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
    }
}
