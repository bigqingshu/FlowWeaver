namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RefreshWorkflowDefinitionDraftStructureState()
    {
        WorkflowDefinitionDraftStructure =
            ReadWorkflowDefinitionDraftStructureFromCache();
        RefreshWorkflowDefinitionDraftNodes();
        ClearSelectedWorkflowDefinitionDraftNodeIfMissing();
        ClearSelectedWorkflowDefinitionDraftConnectionIfMissing();
        ClearSelectedNewDraftConnectionNodesIfMissing();
    }
}
