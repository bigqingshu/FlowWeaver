using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand]
    private void ViewAllRecentEvents()
    {
        SelectedShellPageKey = ShellPageKey.Logs;
    }
}
