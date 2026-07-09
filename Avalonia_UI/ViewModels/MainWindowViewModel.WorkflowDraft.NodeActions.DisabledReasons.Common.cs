namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string? GetWorkflowDefinitionNodeMutationDisabledReason()
    {
        if (IsWorkflowDefinitionDraftBusy)
        {
            return T("action.disabled.busy");
        }

        if (!CanUseEngineActions)
        {
            return T("action.disabled.engine_not_connected");
        }

        if (WorkflowDefinitionDetail is null || !HasWorkflowDefinitionDraft)
        {
            return T("action.disabled.no_workflow_definition");
        }

        if (HasWorkflowDefinitionRevisionConflict)
        {
            return T("action.disabled.revision_conflict");
        }

        return null;
    }
}
