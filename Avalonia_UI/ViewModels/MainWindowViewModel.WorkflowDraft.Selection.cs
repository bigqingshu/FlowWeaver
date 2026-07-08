using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnSelectedWorkflowDefinitionNodeChanged(
        WorkflowDefinitionNodeListItemViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedWorkflowDefinitionNode));
        OnPropertyChanged(nameof(HasNoSelectedWorkflowDefinitionNode));
        ResetDataPreviewSelectionState();
        RefreshSelectedNodeDisplayNameDraftState();
        RefreshSelectedNodeConfigDraftState();
        SelectedRuntimeOptionsNode = value;
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }
}
