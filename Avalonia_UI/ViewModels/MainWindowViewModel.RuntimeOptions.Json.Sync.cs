using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
