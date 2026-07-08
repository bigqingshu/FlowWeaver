using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string workflowDefinitionDraftJson = string.Empty;

    private string originalWorkflowDefinitionJson = string.Empty;

    partial void OnWorkflowDefinitionDraftJsonChanged(string value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraft));
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshSelectedNodeConfigDraftState();
        RefreshRuntimeOptionsDraftState();

        IsWorkflowDefinitionDraftDirty = value != originalWorkflowDefinitionJson;

        if (WorkflowDefinitionValidationMessage == T("definition.draft_valid") ||
            WorkflowDefinitionValidationMessage == T("definition.draft_has_issues") ||
            WorkflowDefinitionValidationMessage == T("definition.validation_failed"))
        {
            WorkflowDefinitionValidationMessage = T("definition.validation_invalidated");
            WorkflowDefinitionValidationErrorMessage = null;
        }

        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
    }
}
