using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public sealed partial class RunLoopMonitorViewModel : ViewModelBase
{
    private const int PageSize = 50;

    private readonly ILoopRunQueryService loopRunQueryService;
    private readonly RunMetadataCache metadataCache;
    private readonly Func<string, string> translate;
    private readonly Func<CancellationToken, Task> refreshDelay;
    private readonly DisplayTextFormatter displayTextFormatter;

    private EngineHostConnectionSettings? settings;
    private string? workflowRunId;
    private CancellationTokenSource? runLoadCancellation;
    private CancellationTokenSource? loopLoadCancellation;
    private CancellationTokenSource? iterationLoadCancellation;
    private CancellationTokenSource? refreshCancellation;
    private int runRequestVersion;
    private int loopRequestVersion;
    private int iterationRequestVersion;
    private bool isResettingSelection;
    private Task pendingLoadTask = Task.CompletedTask;
    private Task pendingRefreshTask = Task.CompletedTask;

    public RunLoopMonitorViewModel(
        ILoopRunQueryService loopRunQueryService,
        RunMetadataCache metadataCache,
        Func<string, string> translate,
        Func<CancellationToken, Task>? refreshDelay = null,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        this.loopRunQueryService = loopRunQueryService;
        this.metadataCache = metadataCache;
        this.translate = translate;
        this.displayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        this.refreshDelay = refreshDelay
            ?? (cancellationToken => Task.Delay(
                TimeSpan.FromMilliseconds(200),
                cancellationToken));
        Message = SelectRunText;
    }

    public ObservableCollection<LoopRunListItemViewModel> Loops { get; } = new();

    public ObservableCollection<LoopIterationListItemViewModel> Iterations { get; } = new();

    public ObservableCollection<LoopIterationNodeListItemViewModel> IterationNodes { get; } = new();

    public ObservableCollection<LoopIterationTableRefListItemViewModel> IterationTableRefs { get; } = new();

    [ObservableProperty]
    private LoopRunListItemViewModel? selectedLoop;

    [ObservableProperty]
    private LoopIterationListItemViewModel? selectedIteration;

    [ObservableProperty]
    private bool isLoadingLoops;

    [ObservableProperty]
    private bool isLoadingIterations;

    [ObservableProperty]
    private bool isLoadingIterationDetails;

    [ObservableProperty]
    private bool hasMoreLoops;

    [ObservableProperty]
    private bool hasMoreIterations;

    [ObservableProperty]
    private string message;

    [ObservableProperty]
    private string? errorMessage;

    public string SectionText => translate("runs.loop_monitor.section");

    public string OverviewText => translate("runs.loop_monitor.overview");

    public string LoopsText => translate("runs.loop_monitor.loops");

    public string IterationsText => translate("runs.loop_monitor.iterations");

    public string LoopDetailsText => translate("runs.loop_monitor.loop_details");

    public string IterationDetailsText => translate("runs.loop_monitor.iteration_details");

    public string NodesText => translate("runs.loop_monitor.nodes");

    public string TablesText => translate("runs.loop_monitor.tables");

    public string LoadMoreText => translate("runs.loop_monitor.load_more");

    public string SelectRunText => translate("runs.loop_monitor.select_run");

    public string EmptyText => translate("runs.loop_monitor.empty");

    public string SelectLoopText => translate("runs.loop_monitor.select_loop");

    public string SelectIterationText => translate("runs.loop_monitor.select_iteration");

    public string LoopRunIdLabel => translate("runs.loop_monitor.loop_run_id");

    public string LoopIdLabel => translate("runs.loop_monitor.loop_id");

    public string StartNodeLabel => translate("runs.loop_monitor.start_node");

    public string JudgeNodeLabel => translate("runs.loop_monitor.judge_node");

    public string StatusLabel => translate("runs.loop_monitor.status");

    public string ProgressLabel => translate("runs.loop_monitor.progress");

    public string ExitReasonLabel => translate("runs.loop_monitor.exit_reason");

    public string StartedLabel => translate("runs.loop_monitor.started");

    public string FinishedLabel => translate("runs.loop_monitor.finished");

    public string DurationLabel => translate("runs.loop_monitor.duration");

    public string ErrorText => translate("runs.loop_monitor.error");

    public string IterationIdLabel => translate("runs.loop_monitor.iteration_id");

    public string IterationIndexLabel => translate("runs.loop_monitor.iteration_index");

    public string InputTableRefLabel => translate("runs.loop_monitor.input_table_ref");

    public string OutputTableRefLabel => translate("runs.loop_monitor.output_table_ref");

    public string FailedNodeRunLabel => translate("runs.loop_monitor.failed_node_run");

    public bool IsBusy => IsLoadingLoops || IsLoadingIterations || IsLoadingIterationDetails;

    public bool HasLoops => Loops.Count > 0;

    public bool HasNoLoops => !HasLoops && !IsLoadingLoops;

    public bool HasIterations => Iterations.Count > 0;

    public bool HasSelectedLoop => SelectedLoop is not null;

    public bool HasSelectedIteration => SelectedIteration is not null;

    public bool HasIterationDetails =>
        IterationNodes.Count > 0 || IterationTableRefs.Count > 0;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public Task WaitForPendingLoadAsync()
    {
        return pendingLoadTask;
    }

    public Task WaitForPendingRefreshAsync()
    {
        return pendingRefreshTask;
    }

    public Task SelectRunAsync(
        EngineHostConnectionSettings connectionSettings,
        string? selectedWorkflowRunId)
    {
        CancelRefreshRequest();
        settings = connectionSettings;
        workflowRunId = selectedWorkflowRunId;
        CancelRunRequests();
        runLoadCancellation = new CancellationTokenSource();
        var requestVersion = ++runRequestVersion;
        ResetAllState();
        pendingLoadTask = LoadLoopsAsync(
            offset: 0,
            append: false,
            requestVersion,
            runLoadCancellation.Token);
        return pendingLoadTask;
    }

    public void QueueRefresh(
        EngineHostConnectionSettings connectionSettings,
        string? affectedWorkflowRunId)
    {
        if (string.IsNullOrWhiteSpace(affectedWorkflowRunId) ||
            !string.Equals(
                affectedWorkflowRunId,
                workflowRunId,
                StringComparison.Ordinal) ||
            !pendingRefreshTask.IsCompleted)
        {
            return;
        }

        refreshCancellation?.Cancel();
        refreshCancellation?.Dispose();
        refreshCancellation = new CancellationTokenSource();
        pendingRefreshTask = RefreshAfterDelayAsync(
            connectionSettings,
            affectedWorkflowRunId,
            refreshCancellation.Token);
    }

    public void RefreshLocalizedText()
    {
        foreach (var loop in Loops)
        {
            loop.RefreshLocalizedText();
        }

        foreach (var iteration in Iterations)
        {
            iteration.RefreshLocalizedText();
        }

        foreach (var node in IterationNodes)
        {
            node.RefreshLocalizedText();
        }

        OnPropertyChanged(nameof(SectionText));
        OnPropertyChanged(nameof(OverviewText));
        OnPropertyChanged(nameof(LoopsText));
        OnPropertyChanged(nameof(IterationsText));
        OnPropertyChanged(nameof(LoopDetailsText));
        OnPropertyChanged(nameof(IterationDetailsText));
        OnPropertyChanged(nameof(NodesText));
        OnPropertyChanged(nameof(TablesText));
        OnPropertyChanged(nameof(LoadMoreText));
        OnPropertyChanged(nameof(SelectRunText));
        OnPropertyChanged(nameof(EmptyText));
        OnPropertyChanged(nameof(SelectLoopText));
        OnPropertyChanged(nameof(SelectIterationText));
        OnPropertyChanged(nameof(LoopRunIdLabel));
        OnPropertyChanged(nameof(LoopIdLabel));
        OnPropertyChanged(nameof(StartNodeLabel));
        OnPropertyChanged(nameof(JudgeNodeLabel));
        OnPropertyChanged(nameof(StatusLabel));
        OnPropertyChanged(nameof(ProgressLabel));
        OnPropertyChanged(nameof(ExitReasonLabel));
        OnPropertyChanged(nameof(StartedLabel));
        OnPropertyChanged(nameof(FinishedLabel));
        OnPropertyChanged(nameof(DurationLabel));
        OnPropertyChanged(nameof(ErrorText));
        OnPropertyChanged(nameof(IterationIdLabel));
        OnPropertyChanged(nameof(IterationIndexLabel));
        OnPropertyChanged(nameof(InputTableRefLabel));
        OnPropertyChanged(nameof(OutputTableRefLabel));
        OnPropertyChanged(nameof(FailedNodeRunLabel));
        if (string.IsNullOrWhiteSpace(workflowRunId))
        {
            Message = SelectRunText;
        }
        else if (Loops.Count == 0 && !IsLoadingLoops && !HasError)
        {
            Message = EmptyText;
        }
        else if (SelectedLoop is null)
        {
            Message = SelectLoopText;
        }
        else if (SelectedIteration is null)
        {
            Message = SelectIterationText;
        }
    }

    partial void OnSelectedLoopChanged(LoopRunListItemViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedLoop));
        if (isResettingSelection)
        {
            return;
        }

        CancelLoopRequests();
        ResetIterationState();
        if (value is null || runLoadCancellation is null)
        {
            Message = HasLoops ? SelectLoopText : EmptyText;
            return;
        }

        loopLoadCancellation = CancellationTokenSource.CreateLinkedTokenSource(
            runLoadCancellation.Token);
        var requestVersion = ++loopRequestVersion;
        pendingLoadTask = LoadIterationsAsync(
            value,
            offset: 0,
            append: false,
            requestVersion,
            loopLoadCancellation.Token);
    }

    partial void OnSelectedIterationChanged(LoopIterationListItemViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedIteration));
        if (isResettingSelection)
        {
            return;
        }

        CancelIterationRequest();
        ResetIterationDetails();
        if (value is null ||
            SelectedLoop is null ||
            loopLoadCancellation is null)
        {
            Message = HasIterations ? SelectIterationText : SelectLoopText;
            return;
        }

        iterationLoadCancellation = CancellationTokenSource.CreateLinkedTokenSource(
            loopLoadCancellation.Token);
        var requestVersion = ++iterationRequestVersion;
        pendingLoadTask = LoadIterationDetailsAsync(
            SelectedLoop,
            value,
            requestVersion,
            iterationLoadCancellation.Token);
    }

    partial void OnIsLoadingLoopsChanged(bool value)
    {
        NotifyBusyStateChanged();
    }

    partial void OnIsLoadingIterationsChanged(bool value)
    {
        NotifyBusyStateChanged();
    }

    partial void OnIsLoadingIterationDetailsChanged(bool value)
    {
        NotifyBusyStateChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }

    [RelayCommand(CanExecute = nameof(CanLoadMoreLoops))]
    private async Task LoadMoreLoopsAsync()
    {
        if (runLoadCancellation is null)
        {
            return;
        }

        var requestVersion = ++runRequestVersion;
        await LoadLoopsAsync(
            Loops.Count,
            append: true,
            requestVersion,
            runLoadCancellation.Token);
    }

    [RelayCommand(CanExecute = nameof(CanLoadMoreIterations))]
    private async Task LoadMoreIterationsAsync()
    {
        if (SelectedLoop is null || loopLoadCancellation is null)
        {
            return;
        }

        var requestVersion = ++loopRequestVersion;
        await LoadIterationsAsync(
            SelectedLoop,
            Iterations.Count,
            append: true,
            requestVersion,
            loopLoadCancellation.Token);
    }

    private bool CanLoadMoreLoops()
    {
        return HasMoreLoops && !IsLoadingLoops && !string.IsNullOrWhiteSpace(workflowRunId);
    }

    private bool CanLoadMoreIterations()
    {
        return HasMoreIterations && !IsLoadingIterations && SelectedLoop is not null;
    }

    private async Task LoadLoopsAsync(
        int offset,
        bool append,
        int requestVersion,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(workflowRunId) || settings is null)
        {
            Message = SelectRunText;
            return;
        }

        IsLoadingLoops = true;
        ErrorMessage = null;
        try
        {
            var requestedRunId = workflowRunId;
            var response = await loopRunQueryService.ListLoopsAsync(
                settings,
                requestedRunId,
                offset,
                PageSize,
                cancellationToken: cancellationToken);
            if (requestVersion != runRequestVersion ||
                !string.Equals(requestedRunId, workflowRunId, StringComparison.Ordinal))
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                ErrorMessage = FormatError(response.Error?.ErrorCode, response.Error?.Message);
                Message = string.Empty;
                return;
            }

            if (!append)
            {
                isResettingSelection = true;
                try
                {
                    SelectedLoop = null;
                    Loops.Clear();
                }
                finally
                {
                    isResettingSelection = false;
                }
            }

            var existingIds = Loops.Select(loop => loop.LoopRunId).ToHashSet(StringComparer.Ordinal);
            foreach (var loop in response.Data)
            {
                if (existingIds.Add(loop.LoopRunId))
                {
                    Loops.Add(new LoopRunListItemViewModel(loop, displayTextFormatter));
                }
            }

            HasMoreLoops = response.Data.Count == PageSize;
            Message = Loops.Count == 0 ? EmptyText : SelectLoopText;
            NotifyLoopCollectionChanged();
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        finally
        {
            if (requestVersion == runRequestVersion)
            {
                IsLoadingLoops = false;
            }
        }
    }

    private async Task LoadIterationsAsync(
        LoopRunListItemViewModel loop,
        int offset,
        bool append,
        int requestVersion,
        CancellationToken cancellationToken)
    {
        if (workflowRunId is null || settings is null)
        {
            return;
        }

        IsLoadingIterations = true;
        ErrorMessage = null;
        try
        {
            var requestedRunId = workflowRunId;
            var response = await loopRunQueryService.ListIterationsAsync(
                settings,
                requestedRunId,
                loop.LoopRunId,
                offset,
                PageSize,
                cancellationToken: cancellationToken);
            if (requestVersion != loopRequestVersion ||
                SelectedLoop?.LoopRunId != loop.LoopRunId ||
                workflowRunId != requestedRunId)
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                ErrorMessage = FormatError(response.Error?.ErrorCode, response.Error?.Message);
                Message = string.Empty;
                return;
            }

            if (!append)
            {
                isResettingSelection = true;
                try
                {
                    SelectedIteration = null;
                    Iterations.Clear();
                }
                finally
                {
                    isResettingSelection = false;
                }
            }

            var existingIds = Iterations
                .Select(iteration => iteration.LoopIterationId)
                .ToHashSet(StringComparer.Ordinal);
            foreach (var iteration in response.Data)
            {
                if (existingIds.Add(iteration.LoopIterationId))
                {
                    Iterations.Add(new LoopIterationListItemViewModel(
                        iteration,
                        displayTextFormatter));
                }
            }

            HasMoreIterations = response.Data.Count == PageSize;
            Message = Iterations.Count == 0 ? SelectLoopText : SelectIterationText;
            NotifyIterationCollectionChanged();
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        finally
        {
            if (requestVersion == loopRequestVersion)
            {
                IsLoadingIterations = false;
            }
        }
    }

    private async Task LoadIterationDetailsAsync(
        LoopRunListItemViewModel loop,
        LoopIterationListItemViewModel iteration,
        int requestVersion,
        CancellationToken cancellationToken)
    {
        if (workflowRunId is null || settings is null)
        {
            return;
        }

        IsLoadingIterationDetails = true;
        ErrorMessage = null;
        try
        {
            var requestedRunId = workflowRunId;
            var nodesTask = metadataCache.GetIterationNodesAsync(
                settings,
                requestedRunId,
                loop.LoopRunId,
                iteration.LoopIterationId,
                cancellationToken);
            var tablesTask = metadataCache.GetIterationTableRefsAsync(
                settings,
                requestedRunId,
                loop.LoopRunId,
                iteration.LoopIterationId,
                cancellationToken: cancellationToken);
            await Task.WhenAll(nodesTask, tablesTask);
            if (requestVersion != iterationRequestVersion ||
                SelectedIteration?.LoopIterationId != iteration.LoopIterationId ||
                workflowRunId != requestedRunId)
            {
                return;
            }

            var nodesResponse = await nodesTask;
            var tablesResponse = await tablesTask;
            if (!nodesResponse.Ok || nodesResponse.Data is null)
            {
                ErrorMessage = FormatError(
                    nodesResponse.Error?.ErrorCode,
                    nodesResponse.Error?.Message);
                return;
            }

            if (!tablesResponse.Ok || tablesResponse.Data is null)
            {
                ErrorMessage = FormatError(
                    tablesResponse.Error?.ErrorCode,
                    tablesResponse.Error?.Message);
                return;
            }

            IterationNodes.Clear();
            foreach (var node in nodesResponse.Data)
            {
                IterationNodes.Add(new LoopIterationNodeListItemViewModel(
                    node,
                    displayTextFormatter,
                    translate));
            }

            IterationTableRefs.Clear();
            foreach (var tableRef in tablesResponse.Data)
            {
                IterationTableRefs.Add(
                    new LoopIterationTableRefListItemViewModel(tableRef));
            }

            Message = string.Empty;
            OnPropertyChanged(nameof(HasIterationDetails));
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        finally
        {
            if (requestVersion == iterationRequestVersion)
            {
                IsLoadingIterationDetails = false;
            }
        }
    }

    private async Task RefreshAfterDelayAsync(
        EngineHostConnectionSettings connectionSettings,
        string affectedWorkflowRunId,
        CancellationToken cancellationToken)
    {
        try
        {
            await refreshDelay(cancellationToken);
            cancellationToken.ThrowIfCancellationRequested();
            metadataCache.InvalidateRun(affectedWorkflowRunId);
            await SelectRunAsync(connectionSettings, affectedWorkflowRunId);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
    }

    private void CancelRunRequests()
    {
        CancelLoopRequests();
        runLoadCancellation?.Cancel();
        runLoadCancellation?.Dispose();
        runLoadCancellation = null;
    }

    private void CancelRefreshRequest()
    {
        refreshCancellation?.Cancel();
        refreshCancellation?.Dispose();
        refreshCancellation = null;
    }

    private void CancelLoopRequests()
    {
        CancelIterationRequest();
        loopLoadCancellation?.Cancel();
        loopLoadCancellation?.Dispose();
        loopLoadCancellation = null;
        loopRequestVersion++;
    }

    private void CancelIterationRequest()
    {
        iterationLoadCancellation?.Cancel();
        iterationLoadCancellation?.Dispose();
        iterationLoadCancellation = null;
        iterationRequestVersion++;
    }

    private void ResetAllState()
    {
        isResettingSelection = true;
        try
        {
            SelectedLoop = null;
            SelectedIteration = null;
        }
        finally
        {
            isResettingSelection = false;
        }

        Loops.Clear();
        ResetIterationState();
        HasMoreLoops = false;
        ErrorMessage = null;
        Message = string.IsNullOrWhiteSpace(workflowRunId) ? SelectRunText : string.Empty;
        NotifyLoopCollectionChanged();
    }

    private void ResetIterationState()
    {
        isResettingSelection = true;
        try
        {
            SelectedIteration = null;
        }
        finally
        {
            isResettingSelection = false;
        }

        Iterations.Clear();
        HasMoreIterations = false;
        ResetIterationDetails();
        NotifyIterationCollectionChanged();
    }

    private void ResetIterationDetails()
    {
        IterationNodes.Clear();
        IterationTableRefs.Clear();
        OnPropertyChanged(nameof(HasIterationDetails));
    }

    private void NotifyLoopCollectionChanged()
    {
        OnPropertyChanged(nameof(HasLoops));
        OnPropertyChanged(nameof(HasNoLoops));
        LoadMoreLoopsCommand.NotifyCanExecuteChanged();
    }

    private void NotifyIterationCollectionChanged()
    {
        OnPropertyChanged(nameof(HasIterations));
        LoadMoreIterationsCommand.NotifyCanExecuteChanged();
    }

    private void NotifyBusyStateChanged()
    {
        OnPropertyChanged(nameof(IsBusy));
        OnPropertyChanged(nameof(HasNoLoops));
        LoadMoreLoopsCommand.NotifyCanExecuteChanged();
        LoadMoreIterationsCommand.NotifyCanExecuteChanged();
    }

    private static string FormatError(string? code, string? message)
    {
        return string.IsNullOrWhiteSpace(code)
            ? message ?? "REQUEST_FAILED"
            : string.IsNullOrWhiteSpace(message)
                ? code
                : $"{code}: {message}";
    }
}
