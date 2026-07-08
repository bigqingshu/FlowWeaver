namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyWorkflowStructuredEditLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(StructuredEditSectionText));
        OnPropertyChanged(nameof(AddNodeText));
        OnPropertyChanged(nameof(CopyNodeText));
        OnPropertyChanged(nameof(DeleteNodeText));
        OnPropertyChanged(nameof(DeleteSelectedNodesText));
        OnPropertyChanged(nameof(MoveNodeUpText));
        OnPropertyChanged(nameof(MoveNodeDownText));
        OnPropertyChanged(nameof(NodeActionsSectionText));
        OnPropertyChanged(nameof(NodeMoveSemanticsText));
        OnPropertyChanged(nameof(WorkflowLinearChainStatusText));
        NotifyWorkflowDefinitionNodeActionDisabledReasonsChanged();
    }
}
