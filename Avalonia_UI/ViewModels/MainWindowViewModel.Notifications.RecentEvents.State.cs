using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isRecentEventsExpanded;

    public ObservableCollection<RecentEventListItemViewModel> RecentEvents { get; } =
        new();

    public bool HasRecentEvents => RecentEvents.Count > 0;

    public bool HasNoRecentEvents => !HasRecentEvents;

    public bool HasMoreRecentEvents => RecentEvents.Count > CollapsedRecentEventCount;

    public IReadOnlyList<RecentEventListItemViewModel> VisibleRecentEvents =>
        RecentEvents.Take(
                IsRecentEventsExpanded
                    ? ExpandedRecentEventCount
                    : CollapsedRecentEventCount)
            .ToArray();

    public string RecentEventsToggleText => IsRecentEventsExpanded
        ? T("recent_events.collapse")
        : T("recent_events.expand");

    private void NotifyRecentEventsChanged()
    {
        OnPropertyChanged(nameof(HasRecentEvents));
        OnPropertyChanged(nameof(HasNoRecentEvents));
        OnPropertyChanged(nameof(HasMoreRecentEvents));
        OnPropertyChanged(nameof(VisibleRecentEvents));
    }

    partial void OnIsRecentEventsExpandedChanged(bool value)
    {
        OnPropertyChanged(nameof(RecentEventsToggleText));
        OnPropertyChanged(nameof(VisibleRecentEvents));
    }
}
