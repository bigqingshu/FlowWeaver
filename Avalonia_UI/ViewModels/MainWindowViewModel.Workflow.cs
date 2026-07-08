using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static bool IsActiveWorkflowStatus(string? status)
    {
        return status == "ACTIVE";
    }
}
