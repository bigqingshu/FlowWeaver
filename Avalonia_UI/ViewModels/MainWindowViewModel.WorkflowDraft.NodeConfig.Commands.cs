using System.Text.Json;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanApplySelectedNodeConfigDraft()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && HasSelectedNodeConfigEditableInputFields;
    }

    [RelayCommand(CanExecute = nameof(CanApplySelectedNodeConfigDraft))]
    private void ApplySelectedNodeConfigDraft()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
            WorkflowDefinitionValidationErrorMessage =
                DisplayTextFormatter.FormatSelectedNodeConfigDraftMissingSelection();
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_config",
                UiNotificationKind.Error);
            return;
        }

        var configResult = NodeConfigEditableFieldInputConfigBuilder.Build(
            SelectedWorkflowDefinitionNode.NodeInstanceId,
            SelectedNodeConfigEditableInputFields);
        if (!configResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
            WorkflowDefinitionValidationErrorMessage =
                FormatNodeConfigApplyErrors(configResult);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_config",
                UiNotificationKind.Error);
            return;
        }

        using var config = JsonDocument.Parse(configResult.ConfigJson);
        var patchResult = NodeConfigDraftJsonPatcher.ApplyConfig(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId,
            config.RootElement);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
            WorkflowDefinitionValidationErrorMessage = patchResult.Warning;
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_config",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage = T("definition.node_config_applied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.node_config",
            UiNotificationKind.Success);
    }

}
