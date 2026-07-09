namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnIsWorkflowDraftJsonAdvancedVisibleChanged(bool value)
    {
        OnPropertyChanged(nameof(ShowAdvancedDraftJsonText));
    }
}
