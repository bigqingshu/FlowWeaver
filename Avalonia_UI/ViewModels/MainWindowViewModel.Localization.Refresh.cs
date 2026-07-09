namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyLocalizedTextChanged()
    {
        NotifyAppShellLocalizedTextChanged();
        NotifyConnectionLocalizedTextChanged();
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
        RefreshLocalizedDerivedState();
    }
}
