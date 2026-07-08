using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private const int MaxRecentEvents = 20;
    private const int CollapsedRecentEventCount = 1;
    private const int ExpandedRecentEventCount = 5;

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

    public string RecentEventsSectionText => T("recent_events.section");

    public string RecentEventsEmptyText => T("recent_events.empty");

    public string RecentEventsViewAllText => T("recent_events.view_all");

    public string RecentEventsToggleText => IsRecentEventsExpanded
        ? T("recent_events.collapse")
        : T("recent_events.expand");

    [RelayCommand]
    private void ViewAllRecentEvents()
    {
        SelectedShellPageKey = ShellPageKey.Logs;
    }

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

    private void AddRecentRuntimeEvent(RuntimeEventDto runtimeEvent)
    {
        AddRecentEvent(
            $"runtime_event.{runtimeEvent.SequenceNumber}",
            UiNotificationKind.Info,
            T("recent_events.source_runtime_event"),
            F(
                "format.received_runtime_event",
                runtimeEvent.EventType,
                runtimeEvent.SequenceNumber),
            FormatRecentRuntimeEventMessage(runtimeEvent));
    }

    private static string FormatRecentRuntimeEventMessage(RuntimeEventDto runtimeEvent)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(runtimeEvent.WorkflowRunId))
        {
            parts.Add($"run {runtimeEvent.WorkflowRunId}");
        }

        if (!string.IsNullOrWhiteSpace(runtimeEvent.NodeRunId))
        {
            parts.Add($"node {runtimeEvent.NodeRunId}");
        }

        return parts.Count == 0 ? string.Empty : string.Join(", ", parts);
    }

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
