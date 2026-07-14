namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyWorkflowDefinitionBasicsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(WorkflowDefinitionSectionText));
        OnPropertyChanged(nameof(DetailsText));
        OnPropertyChanged(nameof(NameLabelText));
        OnPropertyChanged(nameof(VersionLabelText));
        OnPropertyChanged(nameof(RevisionLabelText));
        OnPropertyChanged(nameof(StatusLabelText));
        OnPropertyChanged(nameof(HashLabelText));
        OnPropertyChanged(nameof(UpdatedLabelText));
    }

    private void NotifyWorkflowDefinitionNodesLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(NodesSectionText));
        OnPropertyChanged(nameof(WorkflowNodesSectionText));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCountText));
    }

    private void NotifyWorkflowNodeConfigLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(NodeConfigSectionText));
        OnPropertyChanged(nameof(ApplyNodeConfigText));
        OnPropertyChanged(nameof(ToggleNodeConfigAutoSaveText));
        OnPropertyChanged(nameof(ApplyNodeDisplayNameText));
    }
}
