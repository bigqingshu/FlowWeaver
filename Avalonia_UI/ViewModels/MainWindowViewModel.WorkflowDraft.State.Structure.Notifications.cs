namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyWorkflowDefinitionDraftStructurePresentationChanged()
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraftStructure));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftConnectionCount));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftConnectionCountText));
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraftStructureWarnings));
    }
}
