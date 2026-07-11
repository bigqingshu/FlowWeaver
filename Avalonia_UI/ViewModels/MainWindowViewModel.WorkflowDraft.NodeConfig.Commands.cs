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
        if (SelectedWorkflowDefinitionNode is null)
        {
            ApplySelectedNodeConfigDraftMissingSelectionFailure();
            return;
        }

        if (SelectedNodeSpecializedEditor is not null
            && !SelectedNodeSpecializedEditor.TryPrepareApply(
                out var specializedErrorMessage))
        {
            ApplySelectedNodeConfigDraftSpecializedValidationFailure(
                specializedErrorMessage);
            return;
        }

        var configResult = NodeConfigEditableFieldInputConfigBuilder.Build(
            SelectedWorkflowDefinitionNode.NodeInstanceId,
            SelectedNodeConfigEditableInputFields);
        if (!configResult.Succeeded)
        {
            ApplySelectedNodeConfigDraftConfigBuildFailure(configResult);
            return;
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
            ApplySelectedNodeConfigDraftPatchFailure(patchResult);
            return;
        }

        ApplySelectedNodeConfigDraftSuccess(patchResult);
    }
}
