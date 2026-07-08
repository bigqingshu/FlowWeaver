using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isImportingWorkflow;

    [ObservableProperty]
    private bool isDeletingWorkflow;

    [ObservableProperty]
    private bool isExportingWorkflow;

    private static bool IsActiveWorkflowStatus(string? status)
    {
        return status == "ACTIVE";
    }
}
