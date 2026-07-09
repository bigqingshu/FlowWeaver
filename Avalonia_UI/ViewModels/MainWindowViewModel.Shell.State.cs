using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool isSynchronizingShellSelection;

    [ObservableProperty]
    private ShellPageKey selectedShellPageKey = ShellPageKey.Workflows;

    [ObservableProperty]
    private int selectedShellPageIndex;
}
