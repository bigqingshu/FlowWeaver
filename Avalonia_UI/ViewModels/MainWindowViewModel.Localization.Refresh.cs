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
        OnPropertyChanged(nameof(ConnectionsSectionText));
        OnPropertyChanged(nameof(ShowConnectionsText));
        OnPropertyChanged(nameof(AddConnectionText));
        OnPropertyChanged(nameof(DeleteConnectionText));
        OnPropertyChanged(nameof(ConnectionIdText));
        OnPropertyChanged(nameof(SourceNodeText));
        OnPropertyChanged(nameof(SourcePortText));
        OnPropertyChanged(nameof(TargetNodeText));
        OnPropertyChanged(nameof(TargetPortText));
        OnPropertyChanged(nameof(RecentEventsSectionText));
        OnPropertyChanged(nameof(RecentEventsEmptyText));
        OnPropertyChanged(nameof(RecentEventsViewAllText));
        OnPropertyChanged(nameof(RecentEventsToggleText));
        OnPropertyChanged(nameof(NodeCatalogSectionText));
        OnPropertyChanged(nameof(NodeText));
        OnPropertyChanged(nameof(NodeCatalogEmptyStateText));
        OnPropertyChanged(nameof(InputsText));
        OnPropertyChanged(nameof(OutputsText));
        OnPropertyChanged(nameof(ModeText));
        OnPropertyChanged(nameof(TimeoutText));
        OnPropertyChanged(nameof(DraftJsonSectionText));
        OnPropertyChanged(nameof(ShowAdvancedDraftJsonText));
        OnPropertyChanged(nameof(ValidateText));
        OnPropertyChanged(nameof(SaveText));
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
