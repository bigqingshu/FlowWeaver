namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnWorkflowDefinitionDraftJsonChanged(string value)
    {
        AdvanceWorkflowNodeTableBindingsDraftRevision();
        SynchronizeAdvancedWorkflowDraftJson(value);
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraft));
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshWorkflowLoopRegionsFromDraft();
        RefreshWorkflowNodeTableBindingsFromDraft();
        RefreshSelectedNodeConfigDraftState();
        RefreshRuntimeOptionsDraftState();

        IsWorkflowDefinitionDraftDirty =
            workflowDefinitionDraftDocumentState.IsDirty(value);

        if (WorkflowDefinitionValidationMessage == T("definition.draft_valid") ||
            WorkflowDefinitionValidationMessage == T("definition.draft_has_issues") ||
            WorkflowDefinitionValidationMessage == T("definition.validation_failed"))
        {
            WorkflowDefinitionValidationMessage = T("definition.validation_invalidated");
            WorkflowDefinitionValidationErrorMessage = null;
        }

        NotifyWorkflowDefinitionDraftJsonChangedCommands();
    }
}
