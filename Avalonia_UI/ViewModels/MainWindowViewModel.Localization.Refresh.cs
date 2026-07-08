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
        RefreshLocalizedDerivedState();
    }
}
