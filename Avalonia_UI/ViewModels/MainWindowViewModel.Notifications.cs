using System;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
