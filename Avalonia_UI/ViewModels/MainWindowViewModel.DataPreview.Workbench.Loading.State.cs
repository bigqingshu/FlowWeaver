using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int dataPreviewWorkbenchLoadVersion;

    [ObservableProperty]
    private bool isLoadingDataPreviewWorkbench;
}
