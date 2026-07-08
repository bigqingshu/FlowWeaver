using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RefreshSelectedRuntimeOptionsNodeDraftState(
        RuntimeOptionsDraft? currentDraft = null)
    {
        var draft = currentDraft;
        if (draft is null)
        {
            var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
            draft = readResult.Succeeded ? readResult.Draft : new RuntimeOptionsDraft();
        }

        var selectedNodeFieldState =
            RuntimeOptionsDraftStateMapper.ToSelectedNodeFieldState(
                draft,
                SelectedRuntimeOptionsNode?.NodeInstanceId);
        ApplyRuntimeOptionsSelectedNodeDraftFieldState(selectedNodeFieldState);

        OnPropertyChanged(nameof(HasSelectedRuntimeOptionsNode));
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }
}
