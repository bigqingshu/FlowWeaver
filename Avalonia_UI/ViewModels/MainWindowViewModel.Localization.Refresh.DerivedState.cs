namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RefreshLocalizedDerivedState()
    {
        foreach (var nodeDefinition in NodeDefinitions)
        {
            nodeDefinition.RefreshLocalizedText();
        }

        RefreshShellNavigationItems();
        InvalidateWorkflowDefinitionDraftParseCache();
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshWorkflowLoopRegionsFromDraft();
        RefreshWorkflowNodeTableBindingsFromDraft(force: true);
        WorkflowLoopRegions.RefreshLocalizedText();
        RunLoopMonitor.RefreshLocalizedText();
        BackgroundRunManagement.RefreshLocalizedText();
        RefreshSelectedNodeConfigDraftState();
    }
}
