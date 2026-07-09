using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool hasNotificationCountdown;

    [ObservableProperty]
    private double notificationCountdownProgress;
}
