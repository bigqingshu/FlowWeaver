using System;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnSelectedWorkflowDefinitionNodeChanging(
        WorkflowDefinitionNodeListItemViewModel? value)
    {
        if (!isApplyingSelectedNodeConfigDraft
            && !string.Equals(
                SelectedWorkflowDefinitionNode?.NodeInstanceId,
                value?.NodeInstanceId,
                StringComparison.Ordinal))
        {
            FlushPendingNodeConfigAutoSave();
        }
    }

    partial void OnSelectedWorkflowDefinitionNodeChanged(
        WorkflowDefinitionNodeListItemViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedWorkflowDefinitionNode));
        OnPropertyChanged(nameof(HasNoSelectedWorkflowDefinitionNode));
        ResetDataPreviewSelectionState();
        RefreshSelectedNodeDisplayNameDraftState();
        RefreshSelectedNodeConfigDraftState();
        RefreshWorkflowNodeTableBindingsFromDraft();
        SelectedRuntimeOptionsNode = value;
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }
}
