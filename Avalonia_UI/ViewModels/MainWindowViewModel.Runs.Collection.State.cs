using System.Collections.ObjectModel;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private readonly ObservableCollection<WorkflowRunListItemViewModel>
        runsBeforeBackgroundManagementInitialization = new();

    public ObservableCollection<WorkflowRunListItemViewModel> Runs =>
        BackgroundRunManagement?.Runs ?? runsBeforeBackgroundManagementInitialization;

    public ObservableCollection<NodeRunListItemViewModel> NodeRuns { get; } = new();
}
