using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isRuntimeOptionsJsonEditorExpanded;

    [ObservableProperty]
    private string runtimeOptionsJsonDraft = string.Empty;

    [ObservableProperty]
    private bool isRuntimeOptionsJsonDraftDirty;

    private bool isSynchronizingRuntimeOptionsJsonDraft;

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
