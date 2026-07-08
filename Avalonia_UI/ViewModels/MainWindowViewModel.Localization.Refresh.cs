namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyLocalizedTextChanged()
    {
        NotifyAppShellAndConnectionLocalizedTextChanged();
        NotifyDataPreviewWorkbenchLocalizedTextChanged();
        NotifyWorkflowListAndRunsLocalizedTextChanged();
        NotifyWorkflowDefinitionBasicsLocalizedTextChanged();
        NotifyRuntimeOptionsLocalizedTextChanged();
        NotifyWorkflowStructuredEditLocalizedTextChanged();
        NotifyWorkflowDraftEditorLocalizedTextChanged();
        NotifyWorkflowConnectionsLocalizedTextChanged();
        NotifyRecentEventsLocalizedTextChanged();
        NotifyNodeCatalogLocalizedTextChanged();
        NotifyAdvancedDraftJsonLocalizedTextChanged();
        NotifyRuntimeEventLogLocalizedTextChanged();
        NotifySharedDataLocalizedTextChanged();
        foreach (var nodeDefinition in NodeDefinitions)
        {
            nodeDefinition.RefreshLocalizedText();
        }

        RefreshShellNavigationItems();
        InvalidateWorkflowDefinitionDraftParseCache();
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshSelectedNodeConfigDraftState();
    }
}
