using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
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
    private const int NotificationCountdownTickMilliseconds = 16;
    private static readonly TimeSpan DefaultNotificationAutoDismissAfter =
        TimeSpan.FromSeconds(4);

    private CancellationTokenSource? _notificationCountdownCancellation;

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
    private bool hasNotificationCountdown;

    [ObservableProperty]
    private double notificationCountdownProgress;

    [ObservableProperty]
    private int notificationOpenSequence;

    [ObservableProperty]
    private int notificationUpdateCount;

    [ObservableProperty]
    private bool isRecentEventsExpanded;

    public string NotificationKindText => NotificationKind.ToString();

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

    private void StartNotificationCountdownIfNeeded(TimeSpan? autoDismissAfter)
    {
        CancelNotificationCountdown();

        if (autoDismissAfter is null ||
            autoDismissAfter.Value <= TimeSpan.Zero ||
            IsNotificationSticky)
        {
            HasNotificationCountdown = false;
            NotificationCountdownProgress = 0;
            return;
        }

        HasNotificationCountdown = true;
        NotificationCountdownProgress = 1;

        _notificationCountdownCancellation =
            CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        var cancellationToken = _notificationCountdownCancellation.Token;
        var updateCount = NotificationUpdateCount;
        _ = RunNotificationCountdownAsync(
            autoDismissAfter.Value,
            updateCount,
            cancellationToken);
    }

    private void CancelNotificationCountdown()
    {
        _notificationCountdownCancellation?.Cancel();
        _notificationCountdownCancellation?.Dispose();
        _notificationCountdownCancellation = null;
    }

    private async Task RunNotificationCountdownAsync(
        TimeSpan duration,
        int updateCount,
        CancellationToken cancellationToken)
    {
        var startedAt = DateTimeOffset.Now;

        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                var elapsed = DateTimeOffset.Now - startedAt;
                var remainingRatio =
                    1 - elapsed.TotalMilliseconds / duration.TotalMilliseconds;
                NotificationCountdownProgress = Math.Clamp(remainingRatio, 0, 1);

                if (NotificationCountdownProgress <= 0)
                {
                    break;
                }

                var remainingMilliseconds =
                    duration.TotalMilliseconds - elapsed.TotalMilliseconds;
                var delayMilliseconds = Math.Min(
                    NotificationCountdownTickMilliseconds,
                    Math.Max(1, remainingMilliseconds));
                await Task.Delay(
                    TimeSpan.FromMilliseconds(delayMilliseconds),
                    cancellationToken);
            }

            if (!cancellationToken.IsCancellationRequested &&
                IsNotificationOpen &&
                NotificationUpdateCount == updateCount)
            {
                CloseNotification();
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
    }

    [RelayCommand]
    private void ViewAllRecentEvents()
    {
        SelectedShellPageKey = ShellPageKey.Logs;
    }

    private void ShowWorkflowDefinitionNotification(
        string key,
        UiNotificationKind kind,
        bool isSticky = false)
    {
        ShowNotification(
            key,
            kind,
            WorkflowDefinitionValidationMessage,
            WorkflowDefinitionValidationErrorMessage ?? string.Empty,
            isSticky,
            DefaultNotificationAutoDismissAfter);
    }

    private void ShowConnectionNotification(UiNotificationKind kind)
    {
        ShowNotification(
            "connection.check",
            kind,
            StatusMessage,
            kind == UiNotificationKind.Error ? ErrorMessage ?? string.Empty : string.Empty,
            autoDismissAfter: DefaultNotificationAutoDismissAfter);
    }

    private void ShowWorkflowNotification(string key, UiNotificationKind kind)
    {
        ShowNotification(
            key,
            kind,
            WorkflowMessage,
            kind == UiNotificationKind.Error ? WorkflowErrorMessage ?? string.Empty : string.Empty,
            autoDismissAfter: DefaultNotificationAutoDismissAfter);
    }

    private void ShowDataPreviewNotification(UiNotificationKind kind)
    {
        ShowNotification(
            "data_preview.refresh",
            kind,
            DataPreviewMessage,
            kind == UiNotificationKind.Error ? DataPreviewErrorMessage ?? string.Empty : string.Empty,
            autoDismissAfter: DefaultNotificationAutoDismissAfter);
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

    partial void OnNotificationKindChanged(UiNotificationKind value)
    {
        OnPropertyChanged(nameof(NotificationKindText));
    }
}
