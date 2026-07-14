using System;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanApplySelectedNodeDisplayNameDraft()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.Equals(
                SelectedNodeDisplayNameDraft?.Trim() ?? string.Empty,
                SelectedWorkflowDefinitionNode.DisplayName,
                StringComparison.Ordinal);
    }
}
