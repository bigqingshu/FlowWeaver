using System;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void AddRecentEvent(
        string key,
        UiNotificationKind kind,
        string sourceText,
        string title,
        string message)
    {
        RecentEvents.Insert(
            0,
            new RecentEventListItemViewModel(
                key,
                kind,
                sourceText,
                title,
                message,
                DateTimeOffset.Now));

        while (RecentEvents.Count > MaxRecentEvents)
        {
            RecentEvents.RemoveAt(RecentEvents.Count - 1);
        }

        NotifyRecentEventsChanged();
    }
}
