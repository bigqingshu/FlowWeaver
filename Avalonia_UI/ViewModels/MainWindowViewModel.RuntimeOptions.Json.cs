using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanApplyRuntimeOptionsDraft))]
    private void RegenerateRuntimeOptionsJsonDraft()
    {
        if (!TryBuildRuntimeOptionsDraftFromStructuredInputs(
            out var draft,
            out var errorMessage))
        {
            RuntimeOptionsEditorErrorMessage = errorMessage;
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        SetRuntimeOptionsJsonDraft(
            WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(draft),
            isDirty: false);
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
    }

    private void ApplyRuntimeOptionsJsonDraft()
    {
        var readResult = RuntimeOptionsDraftReader.ReadRuntimeOptionsJson(
            RuntimeOptionsJsonDraft);
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        if (!TryValidateRuntimeOptionsDraft(
            readResult.Draft,
            out var errorMessage))
        {
            RuntimeOptionsEditorErrorMessage = errorMessage;
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        if (ApplyRuntimeOptionsDraftToWorkflow(readResult.Draft))
        {
            SetRuntimeOptionsJsonDraft(
                WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(
                    readResult.Draft),
                isDirty: false);
        }
    }

    private void RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean()
    {
        if (!IsRuntimeOptionsJsonEditorExpanded || IsRuntimeOptionsJsonDraftDirty)
        {
            return;
        }

        if (!TryBuildRuntimeOptionsDraftFromStructuredInputs(
            out var draft,
            out _))
        {
            return;
        }

        SetRuntimeOptionsJsonDraft(
            WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(draft),
            isDirty: false);
    }

    private void SetRuntimeOptionsJsonDraft(string value, bool isDirty)
    {
        isSynchronizingRuntimeOptionsJsonDraft = true;
        RuntimeOptionsJsonDraft = value;
        isSynchronizingRuntimeOptionsJsonDraft = false;
        IsRuntimeOptionsJsonDraftDirty = isDirty;
    }
}
