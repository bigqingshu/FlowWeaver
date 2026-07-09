namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyLocalizedTextChanged()
    {
        NotifyAppShellLocalizedTextChanged();
        NotifyConnectionLocalizedTextChanged();
        NotifyDataPreviewWorkbenchLocalizedTextChanged();
        NotifyWorkflowListLocalizedTextChanged();
        NotifyRunsLocalizedTextChanged();
        NotifyWorkflowDefinitionBasicsLocalizedTextChanged();
        NotifyWorkflowDefinitionNodesLocalizedTextChanged();
        NotifyWorkflowNodeConfigLocalizedTextChanged();
        NotifyRuntimeOptionsLocalizedTextChanged();
        NotifyWorkflowStructuredEditLocalizedTextChanged();
        NotifyWorkflowDraftEditorLocalizedTextChanged();
        NotifyWorkflowConnectionsLocalizedTextChanged();
        NotifyRecentEventsLocalizedTextChanged();
        NotifyNodeCatalogLocalizedTextChanged();
        NotifyAdvancedDraftJsonLocalizedTextChanged();
        NotifyRuntimeEventLogLocalizedTextChanged();
        NotifyTableRefsLocalizedTextChanged();
        NotifySharedPublicationsLocalizedTextChanged();
        RefreshLocalizedDerivedState();
    }
}
