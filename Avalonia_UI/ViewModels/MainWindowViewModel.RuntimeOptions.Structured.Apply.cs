using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanApplyRuntimeOptionsDraft))]
    private void ApplyRuntimeOptionsDraft()
    {
        if (IsRuntimeOptionsJsonEditorExpanded && IsRuntimeOptionsJsonDraftDirty)
        {
            ApplyRuntimeOptionsJsonDraft();
            return;
        }

        ApplyRuntimeOptionsStructuredDraft();
    }

    private void ApplyRuntimeOptionsStructuredDraft()
    {
        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        if (!TryBuildRuntimeOptionsDraftFromStructuredInputs(
            readResult.Draft,
            out var draft,
            out var errorMessage))
        {
            RuntimeOptionsEditorErrorMessage = errorMessage;
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        ApplyRuntimeOptionsDraftToWorkflow(draft);
    }

    private bool ApplyRuntimeOptionsDraftToWorkflow(RuntimeOptionsDraft draft)
    {
        var patchResult = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            WorkflowDefinitionDraftJson,
            draft);
        if (!patchResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return false;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
        WorkflowDefinitionValidationMessage = T("definition.runtime_options_applied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.runtime_options",
            UiNotificationKind.Success);
        if (IsRuntimeOptionsJsonEditorExpanded && !IsRuntimeOptionsJsonDraftDirty)
        {
            SetRuntimeOptionsJsonDraft(
                WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(draft),
                isDirty: false);
        }

        return true;
    }
}
