using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isWorkflowDraftJsonAdvancedVisible;

    partial void OnWorkflowDefinitionErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionError));
    }

    partial void OnIsWorkflowDraftJsonAdvancedVisibleChanged(bool value)
    {
        OnPropertyChanged(nameof(ShowAdvancedDraftJsonText));
    }
}
