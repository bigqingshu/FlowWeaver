using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnWorkflowDefinitionDetailChanged(WorkflowDefinitionDetailViewModel? value)
    {
        ClearWorkflowDefinitionDraftBatchSelection();
        ResetWorkflowDefinitionStructuredEditInput();
        OnPropertyChanged(nameof(HasWorkflowDefinition));
        OnPropertyChanged(nameof(SelectedRunRuntimeOptionsSummaryText));
        RefreshSelectedNodeDisplayNameDraftState();
        RefreshSelectedNodeConfigDraftState();
        RefreshRuntimeOptionsDraftState();
        RefreshBackgroundRunLaunchTargets();
        NotifyWorkflowDefinitionDetailChangedCommands();
    }
}
