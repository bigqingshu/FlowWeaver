using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string newWorkflowName = "Generated table workflow";

    [ObservableProperty]
    private bool isCreatingWorkflow;

    [ObservableProperty]
    private bool isImportingWorkflow;

    [ObservableProperty]
    private bool isDeletingWorkflow;

    [ObservableProperty]
    private bool isExportingWorkflow;

    [ObservableProperty]
    private WorkflowListItemViewModel? selectedWorkflow;

    private static bool IsActiveWorkflowStatus(string? status)
    {
        return status == "ACTIVE";
    }
}
