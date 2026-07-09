using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string sharedPublicationShareNameFilter = string.Empty;

    [ObservableProperty]
    private string sharedPublicationLimitFilter = "100";
}
