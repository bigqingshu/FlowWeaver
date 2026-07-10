using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isWorkflowDraftJsonAdvancedVisible;

    [ObservableProperty]
    private string advancedWorkflowDefinitionDraftJson = string.Empty;
}
