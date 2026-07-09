namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyWorkflowDefinitionNodeActionDisabledReasonsChanged()
    {
        OnPropertyChanged(nameof(CopyWorkflowDefinitionDraftNodeDisabledReasonText));
        OnPropertyChanged(nameof(DeleteWorkflowDefinitionDraftNodeDisabledReasonText));
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText));
        OnPropertyChanged(nameof(MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText));
        OnPropertyChanged(nameof(MoveSelectedWorkflowDefinitionDraftNodeDownDisabledReasonText));
    }
}
