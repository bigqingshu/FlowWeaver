using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int tableRefsLoadVersion;

    [ObservableProperty]
    private bool isLoadingTableRefs;
}
