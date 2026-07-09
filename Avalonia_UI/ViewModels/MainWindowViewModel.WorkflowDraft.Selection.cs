using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private WorkflowDefinitionNodeListItemViewModel? selectedWorkflowDefinitionNode;

    public bool HasSelectedWorkflowDefinitionNode => SelectedWorkflowDefinitionNode is not null;

    public bool HasNoSelectedWorkflowDefinitionNode => SelectedWorkflowDefinitionNode is null;
}
