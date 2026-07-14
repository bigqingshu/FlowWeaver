using System.Linq;
using System.Text.Json;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanApplySelectedNodeConfigDraft))]
    private void ApplySelectedNodeConfigDraft()
    {
        CancelPendingNodeConfigAutoSave();
        TryApplySelectedNodeConfigDraft(automatic: false);
    }

    private bool TryApplySelectedNodeConfigDraft(bool automatic)
    {
        if (automatic && !CanApplySelectedNodeConfigDraft())
        {
            return false;
        }

        isApplyingSelectedNodeConfigDraft = true;
        try
        {
            return TryApplySelectedNodeConfigDraftCore(automatic);
        }
        finally
        {
            isApplyingSelectedNodeConfigDraft = false;
        }
    }

    private bool TryApplySelectedNodeConfigDraftCore(bool automatic)
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            ApplySelectedNodeConfigDraftMissingSelectionFailure(
                showNotification: !automatic);
            return false;
        }

        if (SelectedNodeSpecializedEditor is not null
            && !SelectedNodeSpecializedEditor.TryPrepareApply(
                out var specializedErrorMessage))
        {
            ApplySelectedNodeConfigDraftSpecializedValidationFailure(
                specializedErrorMessage,
                showNotification: !automatic);
            return false;
        }

        var configResult = NodeConfigEditableFieldInputConfigBuilder.Build(
            SelectedWorkflowDefinitionNode.NodeInstanceId,
            SelectedNodeConfigEditableInputFields);
        if (!configResult.Succeeded)
        {
            ApplySelectedNodeConfigDraftConfigBuildFailure(
                configResult,
                showNotification: !automatic);
            return false;
        }

        using var config = JsonDocument.Parse(configResult.ConfigJson);
        var fieldsToDelete = SelectedNodeConfigEditableInputFields
            .Where(field => field.OriginalHasInputValue && !field.HasInputValue)
            .Select(field => field.Name)
            .ToArray();
        var patchResult = NodeConfigDraftJsonPatcher.ApplyPatch(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId,
            config.RootElement,
            fieldsToDelete);
        if (!patchResult.Succeeded)
        {
            ApplySelectedNodeConfigDraftPatchFailure(
                patchResult,
                showNotification: !automatic);
            return false;
        }

        ApplySelectedNodeConfigDraftSuccess(patchResult, automatic);
        return true;
    }
}
