using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string workflowDefinitionDraftJson = string.Empty;

    private string originalWorkflowDefinitionJson = string.Empty;
}
