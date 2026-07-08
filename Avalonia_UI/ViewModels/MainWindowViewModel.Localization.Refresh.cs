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
        OnPropertyChanged(nameof(WorkflowRunFilterText));
        OnPropertyChanged(nameof(RunIdWatermarkText));
        OnPropertyChanged(nameof(NodeRunFilterText));
        OnPropertyChanged(nameof(NodeRunIdWatermarkText));
        OnPropertyChanged(nameof(EventTypeFilterText));
        OnPropertyChanged(nameof(AfterFilterText));
        OnPropertyChanged(nameof(SequenceWatermarkText));
        OnPropertyChanged(nameof(RuntimeText));
        OnPropertyChanged(nameof(LimitText));
        OnPropertyChanged(nameof(RuntimeEventsSectionText));
        OnPropertyChanged(nameof(TableRefsSectionText));
        OnPropertyChanged(nameof(ShareText));
        OnPropertyChanged(nameof(ShareNameWatermarkText));
        OnPropertyChanged(nameof(VersionsText));
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
