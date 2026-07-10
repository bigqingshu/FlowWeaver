using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string selectedWorkflowDefinitionDraftNodeInstanceId = string.Empty;

    public ObservableCollection<WorkflowDefinitionNodeListItemViewModel>
        WorkflowDefinitionDraftNodes { get; } = new();
}
