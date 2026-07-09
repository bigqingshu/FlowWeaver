using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int dataPreviewLoadVersion;

    [ObservableProperty]
    private bool isLoadingDataPreview;
}
