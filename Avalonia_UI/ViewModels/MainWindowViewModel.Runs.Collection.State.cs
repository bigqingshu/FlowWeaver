using System.Collections.ObjectModel;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public ObservableCollection<WorkflowRunListItemViewModel> Runs { get; } = new();

    public ObservableCollection<NodeRunListItemViewModel> NodeRuns { get; } = new();
}
