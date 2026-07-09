namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnIsRuntimeOptionsJsonEditorExpandedChanged(bool value)
    {
        if (value && !IsRuntimeOptionsJsonDraftDirty)
        {
            RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
        }
    }

    partial void OnRuntimeOptionsJsonDraftChanged(string value)
    {
        if (!isSynchronizingRuntimeOptionsJsonDraft)
        {
            IsRuntimeOptionsJsonDraftDirty = true;
        }
    }
}
