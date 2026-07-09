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
}
