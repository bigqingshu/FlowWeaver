using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public sealed record BackgroundRunFilterOptionViewModel(
    string? Value,
    string DisplayText);

public sealed partial class BackgroundRunManagementViewModel : ViewModelBase
{
    public const int PageSize = 50;

    private readonly IBackgroundRunService service;
    private readonly Func<string, string> translate;
    private EngineHostConnectionSettings settings = new();
    private string? workflowId;
    private bool canUseEngineActions;
    private int requestVersion;
    private CancellationTokenSource? requestCancellation;
    private bool suppressFilterRefresh;

    public BackgroundRunManagementViewModel(
        IBackgroundRunService service,
        Func<string, string> translate)
    {
        this.service = service;
        this.translate = translate;
        BuildFilterOptions();
    }

    public event Action<WorkflowRunListItemViewModel?>? SelectedRunChanged;

    public event Action<WorkflowRunListItemViewModel>? RunStarted;

    public event Action<WorkflowRunListItemViewModel>? RunRetried;

    public event Action<string, RunTableCleanupResultDto>? TablesCleaned;

    public ObservableCollection<WorkflowRunListItemViewModel> Runs { get; } = new();

    public ObservableCollection<BackgroundRunFilterOptionViewModel> TriggerSourceOptions { get; } = new();

    public ObservableCollection<BackgroundRunFilterOptionViewModel> RunModeOptions { get; } = new();

    public ObservableCollection<BackgroundRunFilterOptionViewModel> StatusOptions { get; } = new();

    [ObservableProperty]
    private WorkflowRunListItemViewModel? selectedRun;

    [ObservableProperty]
    private BackgroundRunFilterOptionViewModel? selectedTriggerSource;

    [ObservableProperty]
    private BackgroundRunFilterOptionViewModel? selectedRunMode;

    [ObservableProperty]
    private BackgroundRunFilterOptionViewModel? selectedStatus;

    [ObservableProperty]
    private int offset;

    [ObservableProperty]
    private bool hasNextPage;

    [ObservableProperty]
    private bool isLoading;

    [ObservableProperty]
    private bool isStarting;

    [ObservableProperty]
    private bool isRetrying;

    [ObservableProperty]
    private bool isCleaningTables;

    [ObservableProperty]
    private string message = string.Empty;

    [ObservableProperty]
    private string? errorMessage;

    public string TriggerSourceFilterText => translate("runs.background.trigger_filter");

    public string RunModeFilterText => translate("runs.background.mode_filter");

    public string StatusFilterText => translate("runs.background.status_filter");

    public string StartText => translate("runs.background.start");

    public string RetryText => translate("runs.background.retry");

    public string CleanupText => translate("runs.background.cleanup");

    public string PreviousPageText => translate("runs.background.previous_page");

    public string NextPageText => translate("runs.background.next_page");

    public string RetryConfirmText => translate("runs.background.retry_confirm");

    public string CleanupConfirmText => translate("runs.background.cleanup_confirm");

    public string PageText => string.Format(
        translate("runs.background.page_format"),
        Offset / PageSize + 1,
        Offset,
        PageSize);

    public bool HasPreviousPage => Offset > 0;

    public bool IsBusy => IsLoading || IsStarting || IsRetrying || IsCleaningTables;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public bool CanCleanupSelectedRun =>
        canUseEngineActions && SelectedRun?.IsTerminal == true && !IsBusy;

    public bool CanRetrySelectedRun =>
        canUseEngineActions && SelectedRun is not null && !IsBusy;

    public void SetContext(
        EngineHostConnectionSettings connectionSettings,
        string? selectedWorkflowId,
        bool canUseActions)
    {
        settings = connectionSettings;
        canUseEngineActions = canUseActions;
        if (!string.Equals(workflowId, selectedWorkflowId, StringComparison.Ordinal))
        {
            workflowId = selectedWorkflowId;
            CancelRequest();
            Offset = 0;
            Runs.Clear();
            SelectedRun = null;
            HasNextPage = false;
        }

        NotifyCommandStateChanged();
    }

    public async Task LoadPageAsync(
        string? selectWorkflowRunId = null,
        bool resetOffset = false,
        bool allowWhenActionsDisabled = false)
    {
        if (!canUseEngineActions && !allowWhenActionsDisabled)
        {
            return;
        }

        if (resetOffset)
        {
            Offset = 0;
        }

        var requestedOffset = Offset;
        var requestedWorkflowId = workflowId;
        var version = ++requestVersion;
        var cancellation = BeginRequest();
        IsLoading = true;
        Message = translate("runs.background.loading");
        ErrorMessage = null;
        try
        {
            var statuses = string.IsNullOrWhiteSpace(SelectedStatus?.Value)
                ? null
                : new[] { SelectedStatus.Value! };
            var response = await service.ListRunsAsync(
                settings,
                requestedWorkflowId,
                statuses,
                SelectedRunMode?.Value,
                SelectedTriggerSource?.Value,
                requestedOffset,
                PageSize,
                cancellation.Token);
            if (version != requestVersion ||
                !string.Equals(workflowId, requestedWorkflowId, StringComparison.Ordinal))
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                Message = translate("runs.background.load_failed");
                ErrorMessage = DescribeError(response);
                return;
            }

            var previousRunId = selectWorkflowRunId ?? SelectedRun?.WorkflowRunId;
            Runs.Clear();
            foreach (var run in response.Data)
            {
                Runs.Add(new WorkflowRunListItemViewModel(run, translate));
            }

            HasNextPage = response.Data.Count >= PageSize;
            SelectedRun = Runs.FirstOrDefault(run => run.WorkflowRunId == previousRunId)
                ?? Runs.FirstOrDefault();
            Message = string.Format(
                translate("runs.background.loaded_format"),
                Runs.Count,
                requestedOffset,
                PageSize);
        }
        catch (OperationCanceledException) when (cancellation.IsCancellationRequested)
        {
        }
        finally
        {
            if (version == requestVersion)
            {
                IsLoading = false;
            }

            CompleteRequest(cancellation);
        }
    }

    public void SelectRun(WorkflowRunListItemViewModel? run)
    {
        if (!ReferenceEquals(SelectedRun, run))
        {
            SelectedRun = run;
        }
    }

    public async Task<bool> MergeRunAsync(
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        var requestedWorkflowId = workflowId;
        var response = await service.GetRunAsync(
            settings,
            workflowRunId,
            cancellationToken);
        if (!response.Ok || response.Data is null ||
            !string.Equals(workflowId, requestedWorkflowId, StringComparison.Ordinal))
        {
            return false;
        }

        var run = response.Data;
        if (requestedWorkflowId is not null &&
            !string.Equals(run.WorkflowId, requestedWorkflowId, StringComparison.Ordinal))
        {
            return false;
        }

        var existingIndex = FindRunIndex(workflowRunId);
        var wasSelected = string.Equals(
            SelectedRun?.WorkflowRunId,
            workflowRunId,
            StringComparison.Ordinal);
        if (!MatchesCurrentFilters(run))
        {
            if (existingIndex >= 0)
            {
                Runs.RemoveAt(existingIndex);
                if (wasSelected)
                {
                    SelectedRun = Runs.FirstOrDefault();
                }
            }

            return false;
        }

        var merged = new WorkflowRunListItemViewModel(run, translate);
        if (existingIndex >= 0)
        {
            Runs[existingIndex] = merged;
        }
        else if (Offset == 0)
        {
            var pageWasFull = Runs.Count >= PageSize;
            Runs.Insert(0, merged);
            while (Runs.Count > PageSize)
            {
                Runs.RemoveAt(Runs.Count - 1);
            }

            HasNextPage = HasNextPage || pageWasFull;
        }
        else
        {
            return false;
        }

        if (wasSelected || SelectedRun is null)
        {
            SelectedRun = merged;
        }

        return true;
    }

    public void RefreshLocalizedText()
    {
        foreach (var run in Runs)
        {
            run.RefreshLocalizedText();
        }

        var triggerValue = SelectedTriggerSource?.Value;
        var modeValue = SelectedRunMode?.Value;
        var statusValue = SelectedStatus?.Value;
        suppressFilterRefresh = true;
        try
        {
            BuildFilterOptions();
            SelectedTriggerSource = TriggerSourceOptions.First(option => option.Value == triggerValue);
            SelectedRunMode = RunModeOptions.First(option => option.Value == modeValue);
            SelectedStatus = StatusOptions.First(option => option.Value == statusValue);
        }
        finally
        {
            suppressFilterRefresh = false;
        }

        OnPropertyChanged(nameof(TriggerSourceFilterText));
        OnPropertyChanged(nameof(RunModeFilterText));
        OnPropertyChanged(nameof(StatusFilterText));
        OnPropertyChanged(nameof(StartText));
        OnPropertyChanged(nameof(RetryText));
        OnPropertyChanged(nameof(CleanupText));
        OnPropertyChanged(nameof(PreviousPageText));
        OnPropertyChanged(nameof(NextPageText));
        OnPropertyChanged(nameof(RetryConfirmText));
        OnPropertyChanged(nameof(CleanupConfirmText));
        OnPropertyChanged(nameof(PageText));
    }

    partial void OnSelectedRunChanged(WorkflowRunListItemViewModel? value)
    {
        SelectedRunChanged?.Invoke(value);
        NotifyCommandStateChanged();
    }

    partial void OnSelectedTriggerSourceChanged(BackgroundRunFilterOptionViewModel? value)
    {
        QueueFilterRefresh();
    }

    partial void OnSelectedRunModeChanged(BackgroundRunFilterOptionViewModel? value)
    {
        QueueFilterRefresh();
    }

    partial void OnSelectedStatusChanged(BackgroundRunFilterOptionViewModel? value)
    {
        QueueFilterRefresh();
    }

    partial void OnOffsetChanged(int value)
    {
        OnPropertyChanged(nameof(HasPreviousPage));
        OnPropertyChanged(nameof(PageText));
        NotifyCommandStateChanged();
    }

    partial void OnHasNextPageChanged(bool value)
    {
        NotifyCommandStateChanged();
    }

    partial void OnIsLoadingChanged(bool value) => NotifyBusyStateChanged();

    partial void OnIsStartingChanged(bool value) => NotifyBusyStateChanged();

    partial void OnIsRetryingChanged(bool value) => NotifyBusyStateChanged();

    partial void OnIsCleaningTablesChanged(bool value) => NotifyBusyStateChanged();

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }

    [RelayCommand(CanExecute = nameof(CanRefresh))]
    private Task RefreshAsync()
    {
        return LoadPageAsync();
    }

    [RelayCommand(CanExecute = nameof(CanStart))]
    private async Task StartAsync()
    {
        if (workflowId is null)
        {
            return;
        }

        IsStarting = true;
        ErrorMessage = null;
        try
        {
            var response = await service.StartAsync(
                settings,
                workflowId,
                "full",
                cancellationToken: CancellationToken.None);
            if (!response.Ok || response.Data is null)
            {
                Message = translate("runs.background.start_failed");
                ErrorMessage = DescribeError(response);
                return;
            }

            var started = new WorkflowRunListItemViewModel(response.Data, translate);
            RunStarted?.Invoke(started);
            await LoadPageAsync(started.WorkflowRunId, resetOffset: true);
            if (Runs.All(run => run.WorkflowRunId != started.WorkflowRunId))
            {
                Runs.Insert(0, started);
                SelectedRun = started;
            }

            Message = translate("runs.background.started");
        }
        finally
        {
            IsStarting = false;
        }
    }

    [RelayCommand(CanExecute = nameof(CanRetry))]
    private async Task RetryAsync()
    {
        var originalRun = SelectedRun;
        if (originalRun is null)
        {
            return;
        }

        IsRetrying = true;
        ErrorMessage = null;
        try
        {
            var response = await service.RetryAsync(
                settings,
                originalRun.WorkflowRunId,
                cancellationToken: CancellationToken.None);
            if (!response.Ok || response.Data is null)
            {
                Message = translate("runs.background.retry_failed");
                ErrorMessage = DescribeError(response);
                return;
            }

            var retried = new WorkflowRunListItemViewModel(response.Data, translate);
            RunRetried?.Invoke(retried);
            await LoadPageAsync(retried.WorkflowRunId, resetOffset: true);
            if (Runs.All(run => run.WorkflowRunId != retried.WorkflowRunId))
            {
                Runs.Insert(0, retried);
                SelectedRun = retried;
            }

            Message = translate("runs.background.retried");
        }
        finally
        {
            IsRetrying = false;
        }
    }

    [RelayCommand(CanExecute = nameof(CanCleanup))]
    private async Task CleanupTablesAsync()
    {
        var run = SelectedRun;
        if (run is null || !run.IsTerminal)
        {
            return;
        }

        IsCleaningTables = true;
        ErrorMessage = null;
        try
        {
            var response = await service.CleanupTablesAsync(
                settings,
                run.WorkflowRunId,
                CancellationToken.None);
            if (!response.Ok || response.Data is null)
            {
                Message = translate("runs.background.cleanup_failed");
                ErrorMessage = DescribeError(response);
                return;
            }

            TablesCleaned?.Invoke(run.WorkflowRunId, response.Data);
            Message = string.Format(
                translate("runs.background.cleaned_format"),
                response.Data.CleanedCount,
                response.Data.SkippedCount,
                response.Data.FailedCount);
        }
        finally
        {
            IsCleaningTables = false;
        }
    }

    [RelayCommand(CanExecute = nameof(CanPreviousPage))]
    private Task PreviousPageAsync()
    {
        Offset = Math.Max(0, Offset - PageSize);
        return LoadPageAsync();
    }

    [RelayCommand(CanExecute = nameof(CanNextPage))]
    private Task NextPageAsync()
    {
        Offset += PageSize;
        return LoadPageAsync();
    }

    private bool CanRefresh() => canUseEngineActions && !IsBusy;

    private bool CanStart() =>
        canUseEngineActions && !string.IsNullOrWhiteSpace(workflowId) && !IsBusy;

    private bool CanRetry() => CanRetrySelectedRun;

    private bool CanCleanup() => CanCleanupSelectedRun;

    private bool CanPreviousPage() =>
        canUseEngineActions && HasPreviousPage && !IsBusy;

    private bool CanNextPage() =>
        canUseEngineActions && HasNextPage && !IsBusy;

    private void QueueFilterRefresh()
    {
        if (suppressFilterRefresh || !canUseEngineActions)
        {
            return;
        }

        Offset = 0;
        _ = LoadPageAsync();
    }

    private CancellationTokenSource BeginRequest()
    {
        CancelRequest();
        requestCancellation = new CancellationTokenSource();
        return requestCancellation;
    }

    private void CancelRequest()
    {
        requestCancellation?.Cancel();
        requestCancellation?.Dispose();
        requestCancellation = null;
    }

    private void CompleteRequest(CancellationTokenSource request)
    {
        if (ReferenceEquals(requestCancellation, request))
        {
            requestCancellation = null;
        }

        request.Dispose();
    }

    private void NotifyBusyStateChanged()
    {
        OnPropertyChanged(nameof(IsBusy));
        OnPropertyChanged(nameof(CanCleanupSelectedRun));
        OnPropertyChanged(nameof(CanRetrySelectedRun));
        NotifyCommandStateChanged();
    }

    private void NotifyCommandStateChanged()
    {
        RefreshCommand.NotifyCanExecuteChanged();
        StartCommand.NotifyCanExecuteChanged();
        RetryCommand.NotifyCanExecuteChanged();
        CleanupTablesCommand.NotifyCanExecuteChanged();
        PreviousPageCommand.NotifyCanExecuteChanged();
        NextPageCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(CanCleanupSelectedRun));
        OnPropertyChanged(nameof(CanRetrySelectedRun));
    }

    private void BuildFilterOptions()
    {
        TriggerSourceOptions.Clear();
        TriggerSourceOptions.Add(new(null, translate("runs.background.filter_all")));
        TriggerSourceOptions.Add(new("manual", translate("runs.trigger.manual")));
        TriggerSourceOptions.Add(new(
            "background_manual",
            translate("runs.trigger.background_manual")));

        RunModeOptions.Clear();
        RunModeOptions.Add(new(null, translate("runs.background.filter_all")));
        RunModeOptions.Add(new("full", translate("runs.mode.full")));
        RunModeOptions.Add(new("preview_to_node", translate("runs.mode.preview_to_node")));

        StatusOptions.Clear();
        StatusOptions.Add(new(null, translate("runs.background.filter_all")));
        foreach (var status in new[]
        {
            "PENDING",
            "RUNNING",
            "SUCCEEDED",
            "FAILED",
            "CANCELLED",
            "ABORTED",
        })
        {
            StatusOptions.Add(new(status, status));
        }

        SelectedTriggerSource ??= TriggerSourceOptions[0];
        SelectedRunMode ??= RunModeOptions[0];
        SelectedStatus ??= StatusOptions[0];
    }

    private int FindRunIndex(string workflowRunId)
    {
        for (var index = 0; index < Runs.Count; index++)
        {
            if (string.Equals(
                    Runs[index].WorkflowRunId,
                    workflowRunId,
                    StringComparison.Ordinal))
            {
                return index;
            }
        }

        return -1;
    }

    private bool MatchesCurrentFilters(WorkflowRunDto run)
    {
        return MatchesFilter(SelectedStatus?.Value, run.Status)
            && MatchesFilter(SelectedRunMode?.Value, run.RunMode)
            && MatchesFilter(SelectedTriggerSource?.Value, run.TriggerSource);
    }

    private static bool MatchesFilter(string? filter, string value)
    {
        return string.IsNullOrWhiteSpace(filter)
            || string.Equals(filter, value, StringComparison.Ordinal);
    }

    private static string DescribeError<T>(ApiResponseEnvelope<T> response)
    {
        return response.Error?.Message ?? response.Error?.ErrorCode ?? "UNKNOWN_ERROR";
    }
}
