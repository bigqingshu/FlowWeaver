using System;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

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

    public void ShowNotification(
        string key,
        UiNotificationKind kind,
        string title,
        string message,
        bool isSticky = false,
        TimeSpan? autoDismissAfter = null)
    {
        var normalizedKey = string.IsNullOrWhiteSpace(key)
            ? "default"
            : key.Trim();
        var shouldStartOpenAnimation =
            !IsNotificationOpen
            || !string.Equals(NotificationKey, normalizedKey, StringComparison.Ordinal);

        NotificationKey = normalizedKey;
        NotificationKind = kind;
        NotificationTitle = title ?? string.Empty;
        NotificationMessage = message ?? string.Empty;
        NotificationUpdatedAt = DateTimeOffset.Now;
        IsNotificationSticky = isSticky || kind == UiNotificationKind.Error;
        NotificationAutoDismissAfter = IsNotificationSticky ? null : autoDismissAfter;
        NotificationUpdateCount++;
        StartNotificationCountdownIfNeeded(NotificationAutoDismissAfter);
        AddRecentEvent(
            normalizedKey,
            kind,
            T("recent_events.source_notification"),
            NotificationTitle,
            NotificationMessage);

        if (shouldStartOpenAnimation)
        {
            NotificationOpenSequence++;
        }

        IsNotificationOpen = true;
    }

    [RelayCommand]
    private void CloseNotification()
    {
        CancelNotificationCountdown();
        IsNotificationOpen = false;
        NotificationAutoDismissAfter = null;
        HasNotificationCountdown = false;
        NotificationCountdownProgress = 0;
    }

    partial void OnNotificationKindChanged(UiNotificationKind value)
    {
        OnPropertyChanged(nameof(NotificationKindText));
    }
}
