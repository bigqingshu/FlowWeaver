using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
