using System.Collections.Generic;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanResetRuntimeOptionsSelectedNodeOverride()
    {
        return CanApplyRuntimeOptionsDraft()
            && SelectedRuntimeOptionsNode is not null;
    }

    [RelayCommand(CanExecute = nameof(CanResetRuntimeOptionsSelectedNodeOverride))]
    private void ResetRuntimeOptionsSelectedNodeOverride()
    {
        if (SelectedRuntimeOptionsNode is null)
        {
            return;
        }

        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        var nodeOverrides =
            new Dictionary<string, RuntimeOptionsNodeOverrideDraft>(
                readResult.Draft.NodeOverrides);
        nodeOverrides.Remove(SelectedRuntimeOptionsNode.NodeInstanceId);
        var draft = readResult.Draft with
        {
            NodeOverrides = nodeOverrides,
        };
        var patchResult = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            WorkflowDefinitionDraftJson,
            draft);
        if (!patchResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        RefreshSelectedRuntimeOptionsNodeDraftState(draft);
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
        WorkflowDefinitionValidationMessage =
            T("definition.runtime_options_node_override_reset");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.runtime_options",
            UiNotificationKind.Success);
    }
}
