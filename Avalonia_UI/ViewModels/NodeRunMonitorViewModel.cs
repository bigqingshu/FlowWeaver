using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public sealed record NodeRunStatusFilterOptionViewModel(
    string? Value,
    string DisplayText);

public sealed partial class NodeRunMonitorViewModel : ViewModelBase
{
    public const int PageSize = 100;

    private readonly IRunTableDirectoryService service;
    private readonly Func<string, string> translate;
    private readonly DisplayTextFormatter displayTextFormatter;
    private EngineHostConnectionSettings? settings;
    private string? workflowRunId;
    private bool canUseActions;
    private bool hasLoaded;
    private bool suppressFilterLoad;
    private CancellationTokenSource? loadCancellation;
    private int requestVersion;
    private Task pendingLoadTask = Task.CompletedTask;

    public NodeRunMonitorViewModel(
        IRunTableDirectoryService service,
        Func<string, string> translate,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        this.service = service;
        this.translate = translate;
        this.displayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        suppressFilterLoad = true;
        BuildStatusOptions();
        SelectedStatus = StatusOptions[0];
        suppressFilterLoad = false;
        Message = SelectRunText;
    }

    public ObservableCollection<NodeRunListItemViewModel> Nodes { get; } = new();

    public ObservableCollection<NodeRunStatusFilterOptionViewModel> StatusOptions { get; } = new();

    [ObservableProperty]
    private NodeRunListItemViewModel? selectedNodeRun;

    [ObservableProperty]
    private NodeRunStatusFilterOptionViewModel? selectedStatus;

    [ObservableProperty]
    private int offset;

    [ObservableProperty]
    private int total;

    [ObservableProperty]
    private bool hasNextPage;

    [ObservableProperty]
    private bool isLoading;

    [ObservableProperty]
    private string message;

    [ObservableProperty]
    private string? errorMessage;

    public string SectionText => translate("node_runs.section");

    public string RefreshText => translate("common.refresh");

    public string StatusFilterText => translate("node_runs.status_filter");

    public string PreviousPageText => translate("runs.background.previous_page");

    public string NextPageText => translate("runs.background.next_page");

    public string DetailsText => translate("node_runs.details");

    public string SelectRunText => translate("node_runs.select_run");

    public string SelectNodeText => translate("node_runs.select_node");

    public string NodeRunIdLabel => translate("node_runs.node_run_id");

    public string NodeLabel => translate("node_runs.node");

    public string StatusLabel => translate("node_runs.status");

    public string ExecutorLabel => translate("node_runs.executor");

    public string StartedLabel => translate("node_runs.started");

    public string FinishedLabel => translate("node_runs.finished");

    public string DurationLabel => translate("node_runs.duration");

    public string HeartbeatLabel => translate("node_runs.heartbeat");

    public string StateVersionLabel => translate("node_runs.state_version");

    public string ErrorText => translate("node_runs.error");

    public string PageText => string.Format(
        CultureInfo.CurrentCulture,
        translate("node_runs.page_format"),
        Offset / PageSize + 1,
        Total,
        Offset,
        PageSize);

    public bool HasPreviousPage => Offset > 0;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public bool HasSelectedNodeRun => SelectedNodeRun is not null;

    public Task WaitForPendingLoadAsync()
    {
        return pendingLoadTask;
    }

    public Task SelectRunAsync(
        EngineHostConnectionSettings connectionSettings,
        string? selectedWorkflowRunId,
        bool actionsEnabled)
    {
        var normalizedRunId = string.IsNullOrWhiteSpace(selectedWorkflowRunId)
            ? null
            : selectedWorkflowRunId.Trim();
        var contextChanged = settings is null
            || !string.Equals(settings.BaseUrl, connectionSettings.BaseUrl, StringComparison.Ordinal)
            || !string.Equals(settings.Token, connectionSettings.Token, StringComparison.Ordinal)
            || !string.Equals(workflowRunId, normalizedRunId, StringComparison.Ordinal);

        settings = connectionSettings;
        workflowRunId = normalizedRunId;
        canUseActions = actionsEnabled;
        NotifyCommandStateChanged();
        if (!contextChanged)
        {
            if (!canUseActions)
            {
                CancelRequest();
            }
            else if (workflowRunId is not null && !hasLoaded && !IsLoading)
            {
                QueueLoad(resetOffset: true);
            }

            return pendingLoadTask;
        }

        CancelRequest();
        Offset = 0;
        Total = 0;
        HasNextPage = false;
        hasLoaded = false;
        Nodes.Clear();
        SelectedNodeRun = null;
        ErrorMessage = null;
        Message = workflowRunId is null ? SelectRunText : translate("node_runs.ready");
        if (workflowRunId is not null && canUseActions)
        {
            QueueLoad(resetOffset: true);
        }

        return pendingLoadTask;
    }

    public void RefreshLocalizedText()
    {
        foreach (var node in Nodes)
        {
            node.RefreshLocalizedText();
        }

        var statusValue = SelectedStatus?.Value;
        suppressFilterLoad = true;
        try
        {
            BuildStatusOptions();
            SelectedStatus = StatusOptions.First(option => option.Value == statusValue);
        }
        finally
        {
            suppressFilterLoad = false;
        }

        OnPropertyChanged(nameof(SectionText));
        OnPropertyChanged(nameof(RefreshText));
        OnPropertyChanged(nameof(StatusFilterText));
        OnPropertyChanged(nameof(PreviousPageText));
        OnPropertyChanged(nameof(NextPageText));
        OnPropertyChanged(nameof(DetailsText));
        OnPropertyChanged(nameof(SelectRunText));
        OnPropertyChanged(nameof(SelectNodeText));
        OnPropertyChanged(nameof(NodeRunIdLabel));
        OnPropertyChanged(nameof(NodeLabel));
        OnPropertyChanged(nameof(StatusLabel));
        OnPropertyChanged(nameof(ExecutorLabel));
        OnPropertyChanged(nameof(StartedLabel));
        OnPropertyChanged(nameof(FinishedLabel));
        OnPropertyChanged(nameof(DurationLabel));
        OnPropertyChanged(nameof(HeartbeatLabel));
        OnPropertyChanged(nameof(StateVersionLabel));
        OnPropertyChanged(nameof(ErrorText));
        OnPropertyChanged(nameof(PageText));

        if (workflowRunId is null)
        {
            Message = SelectRunText;
        }
        else if (!IsLoading && Nodes.Count == 0 && !HasError)
        {
            Message = translate("node_runs.empty");
        }
        else if (!IsLoading && !HasError)
        {
            Message = SelectedNodeRun is null ? SelectNodeText : translate("node_runs.loaded");
        }
    }

    partial void OnSelectedStatusChanged(NodeRunStatusFilterOptionViewModel? value)
    {
        if (!suppressFilterLoad && workflowRunId is not null && canUseActions)
        {
            QueueLoad(resetOffset: true);
        }
    }

    partial void OnSelectedNodeRunChanged(NodeRunListItemViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedNodeRun));
        if (!IsLoading && Nodes.Count > 0 && !HasError)
        {
            Message = value is null ? SelectNodeText : translate("node_runs.loaded");
        }
    }

    partial void OnOffsetChanged(int value)
    {
        OnPropertyChanged(nameof(HasPreviousPage));
        OnPropertyChanged(nameof(PageText));
        NotifyCommandStateChanged();
    }

    partial void OnTotalChanged(int value)
    {
        OnPropertyChanged(nameof(PageText));
    }

    partial void OnHasNextPageChanged(bool value)
    {
        NotifyCommandStateChanged();
    }

    partial void OnIsLoadingChanged(bool value)
    {
        NotifyCommandStateChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }

    [RelayCommand(CanExecute = nameof(CanRefresh))]
    private async Task RefreshAsync()
    {
        QueueLoad(resetOffset: false);
        await pendingLoadTask;
    }

    [RelayCommand(CanExecute = nameof(CanPreviousPage))]
    private async Task PreviousPageAsync()
    {
        Offset = Math.Max(0, Offset - PageSize);
        QueueLoad(resetOffset: false);
        await pendingLoadTask;
    }

    [RelayCommand(CanExecute = nameof(CanNextPage))]
    private async Task NextPageAsync()
    {
        Offset += PageSize;
        QueueLoad(resetOffset: false);
        await pendingLoadTask;
    }

    private bool CanRefresh()
    {
        return canUseActions && workflowRunId is not null && !IsLoading;
    }

    private bool CanPreviousPage()
    {
        return CanRefresh() && HasPreviousPage;
    }

    private bool CanNextPage()
    {
        return CanRefresh() && HasNextPage;
    }

    private void QueueLoad(bool resetOffset)
    {
        if (!canUseActions || settings is null || workflowRunId is null)
        {
            return;
        }

        if (resetOffset)
        {
            Offset = 0;
        }

        CancelRequest();
        loadCancellation = new CancellationTokenSource();
        var version = ++requestVersion;
        var requestedRunId = workflowRunId;
        var requestedOffset = Offset;
        var statuses = string.IsNullOrWhiteSpace(SelectedStatus?.Value)
            ? null
            : new[] { SelectedStatus.Value! };
        pendingLoadTask = LoadPageAsync(
            settings,
            requestedRunId,
            requestedOffset,
            statuses,
            version,
            loadCancellation.Token);
    }

    private async Task LoadPageAsync(
        EngineHostConnectionSettings requestedSettings,
        string requestedRunId,
        int requestedOffset,
        IReadOnlyCollection<string>? statuses,
        int version,
        CancellationToken cancellationToken)
    {
        IsLoading = true;
        Message = translate("node_runs.loading");
        ErrorMessage = null;
        try
        {
            var response = await service.ListNodeRunsAsync(
                requestedSettings,
                requestedRunId,
                requestedOffset,
                PageSize,
                statuses,
                cancellationToken);
            if (IsStale(version, requestedRunId, requestedOffset))
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                hasLoaded = true;
                Message = translate("node_runs.refresh_failed");
                ErrorMessage = DescribeError(response);
                return;
            }

            var previousNodeRunId = SelectedNodeRun?.NodeRunId;
            hasLoaded = true;
            Nodes.Clear();
            foreach (var node in response.Data.Items)
            {
                Nodes.Add(new NodeRunListItemViewModel(node, displayTextFormatter));
            }

            Offset = response.Data.Offset;
            Total = response.Data.Total;
            HasNextPage = response.Data.HasMore;
            SelectedNodeRun = Nodes.FirstOrDefault(node => node.NodeRunId == previousNodeRunId);
            Message = Nodes.Count == 0
                ? translate("node_runs.empty")
                : SelectNodeText;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception exception)
        {
            if (!IsStale(version, requestedRunId, requestedOffset))
            {
                hasLoaded = true;
                Message = translate("node_runs.refresh_failed");
                ErrorMessage = exception.Message;
            }
        }
        finally
        {
            if (!IsStale(version, requestedRunId, requestedOffset))
            {
                IsLoading = false;
            }
        }
    }

    private bool IsStale(int version, string requestedRunId, int requestedOffset)
    {
        return version != requestVersion
            || !string.Equals(workflowRunId, requestedRunId, StringComparison.Ordinal)
            || Offset != requestedOffset;
    }

    private void CancelRequest()
    {
        requestVersion++;
        loadCancellation?.Cancel();
        loadCancellation?.Dispose();
        loadCancellation = null;
        IsLoading = false;
    }

    private void NotifyCommandStateChanged()
    {
        RefreshCommand.NotifyCanExecuteChanged();
        PreviousPageCommand.NotifyCanExecuteChanged();
        NextPageCommand.NotifyCanExecuteChanged();
    }

    private void BuildStatusOptions()
    {
        StatusOptions.Clear();
        StatusOptions.Add(new(null, translate("runs.background.filter_all")));
        foreach (var status in new[]
        {
            "PENDING",
            "READY",
            "WAITING_DEPENDENCY",
            "QUEUED",
            "RUNNING",
            "LONG_RUNNING",
            "CANCEL_REQUESTED",
            "SUSPECTED_HUNG",
            "TIMED_OUT",
            "SUCCEEDED",
            "FAILED",
            "CANCELLED",
            "SKIPPED",
            "ABORTED",
        })
        {
            StatusOptions.Add(new(status, displayTextFormatter.FormatRuntimeStatus(status)));
        }
    }

    private static string DescribeError<T>(ApiResponseEnvelope<T> response)
    {
        return response.Error?.Message ?? response.Error?.ErrorCode ?? "UNKNOWN_ERROR";
    }
}
