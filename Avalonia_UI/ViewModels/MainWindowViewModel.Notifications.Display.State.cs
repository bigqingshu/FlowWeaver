using System;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isNotificationOpen;

    [ObservableProperty]
    private string notificationKey = string.Empty;

    [ObservableProperty]
    private UiNotificationKind notificationKind = UiNotificationKind.Info;

    [ObservableProperty]
    private string notificationTitle = string.Empty;

    [ObservableProperty]
    private string notificationMessage = string.Empty;

    [ObservableProperty]
    private DateTimeOffset? notificationUpdatedAt;

    [ObservableProperty]
    private bool isNotificationSticky;

    [ObservableProperty]
    private TimeSpan? notificationAutoDismissAfter;

    [ObservableProperty]
    private int notificationOpenSequence;

    [ObservableProperty]
    private int notificationUpdateCount;

    public string NotificationKindText => NotificationKind.ToString();

    partial void OnNotificationKindChanged(UiNotificationKind value)
    {
        OnPropertyChanged(nameof(NotificationKindText));
    }
}
