using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string sharedPublicationVersionShareNameFilter = string.Empty;

    [ObservableProperty]
    private string sharedPublicationVersionLimitFilter = "100";

    partial void OnSharedPublicationVersionShareNameFilterChanged(string value)
    {
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }
}
