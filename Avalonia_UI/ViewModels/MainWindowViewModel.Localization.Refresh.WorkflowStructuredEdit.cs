namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyWorkflowStructuredEditSectionLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(StructuredEditSectionText));
    }

    private void NotifyWorkflowStructuredEditNodeActionsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(AddNodeText));
        OnPropertyChanged(nameof(CopyNodeText));
        OnPropertyChanged(nameof(DeleteNodeText));
        OnPropertyChanged(nameof(DeleteSelectedNodesText));
        OnPropertyChanged(nameof(MoveNodeUpText));
        OnPropertyChanged(nameof(MoveNodeDownText));
        OnPropertyChanged(nameof(NodeActionsSectionText));
        OnPropertyChanged(nameof(NodeMoveSemanticsText));
    }

    private void NotifyWorkflowStructuredEditStatusLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(WorkflowLinearChainStatusText));
        NotifyWorkflowDefinitionNodeActionDisabledReasonsChanged();
    }
}
