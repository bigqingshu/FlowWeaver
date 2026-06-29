using System;
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

public partial class MainWindowViewModel : ViewModelBase
{
    private const int MaxRuntimeEvents = 50;

    private readonly IEngineHostApiClient _apiClient;
    private readonly EngineHostHealthClient _healthClient;
    private readonly IEngineHostRuntimeEventStreamClient _runtimeEventStreamClient;
    private readonly Func<CancellationToken, Task> _runtimeEventReconnectDelay;
    private readonly IConnectionSettingsStore _connectionSettingsStore;

    private readonly CancellationTokenSource _shutdown = new();
    private CancellationTokenSource? _runtimeEventStreamCancellation;
    private Task? _runtimeEventStreamTask;

    [ObservableProperty]
    private string baseUrl = EngineHostConnectionSettings.DefaultBaseUrl;

    [ObservableProperty]
    private string token = string.Empty;

    [ObservableProperty]
    private ConnectionStatus connectionStatus = ConnectionStatus.Disconnected;

    [ObservableProperty]
    private string statusMessage = "Disconnected.";

    [ObservableProperty]
    private string? errorMessage;

    [ObservableProperty]
    private bool isLoadingWorkflows;

    [ObservableProperty]
    private bool isStartingWorkflow;

    [ObservableProperty]
    private WorkflowListItemViewModel? selectedWorkflow;

    [ObservableProperty]
    private string workflowMessage = "No workflows loaded.";

    [ObservableProperty]
    private string? workflowErrorMessage;

    [ObservableProperty]
    private string? lastStartedRunId;

    [ObservableProperty]
    private string? lastStartedRunStatus;

    [ObservableProperty]
    private bool isLoadingRuns;

    [ObservableProperty]
    private bool isCancellingRun;

    [ObservableProperty]
    private WorkflowRunListItemViewModel? selectedRun;

    [ObservableProperty]
    private string runMessage = "No runs loaded.";

    [ObservableProperty]
    private string? runErrorMessage;

    [ObservableProperty]
    private bool isLoadingNodeRuns;

    [ObservableProperty]
    private string nodeRunMessage = "Select a run to load node status.";

    [ObservableProperty]
    private string? nodeRunErrorMessage;

    [ObservableProperty]
    private bool isRuntimeEventStreamRunning;

    [ObservableProperty]
    private bool isRuntimeEventStreamConnected;

    [ObservableProperty]
    private string runtimeEventStreamMessage = "Event stream disconnected.";

    [ObservableProperty]
    private string? runtimeEventStreamErrorMessage;

    [ObservableProperty]
    private long? lastRuntimeEventSequenceNumber;

    [ObservableProperty]
    private string logWorkflowRunIdFilter = string.Empty;

    [ObservableProperty]
    private string logNodeRunIdFilter = string.Empty;

    [ObservableProperty]
    private string logEventTypeFilter = string.Empty;

    [ObservableProperty]
    private string runtimeEventAfterSequenceNumberFilter = string.Empty;

    [ObservableProperty]
    private string runtimeEventLimitFilter = "100";

    [ObservableProperty]
    private bool isLoadingRuntimeEventLog;

    [ObservableProperty]
    private string runtimeEventLogMessage = "No runtime events loaded.";

    [ObservableProperty]
    private string? runtimeEventLogErrorMessage;

    [ObservableProperty]
    private bool isLoadingAuditEventLog;

    [ObservableProperty]
    private string auditEventLogMessage = "No audit events loaded.";

    [ObservableProperty]
    private string? auditEventLogErrorMessage;

    [ObservableProperty]
    private bool isLoadingTableRefs;

    [ObservableProperty]
    private string tableRefMessage = "Select a run to load table refs.";

    [ObservableProperty]
    private string? tableRefErrorMessage;

    [ObservableProperty]
    private string sharedPublicationShareNameFilter = string.Empty;

    [ObservableProperty]
    private string sharedPublicationLimitFilter = "100";

    [ObservableProperty]
    private bool isLoadingSharedPublications;

    [ObservableProperty]
    private SharedPublicationListItemViewModel? selectedSharedPublication;

    [ObservableProperty]
    private string sharedPublicationMessage = "No shared publications loaded.";

    [ObservableProperty]
    private string? sharedPublicationErrorMessage;

    [ObservableProperty]
    private string sharedPublicationVersionShareNameFilter = string.Empty;

    [ObservableProperty]
    private string sharedPublicationVersionLimitFilter = "100";

    [ObservableProperty]
    private bool isLoadingSharedPublicationVersions;

    [ObservableProperty]
    private string sharedPublicationVersionMessage =
        "Select or enter a share name to load versions.";

    [ObservableProperty]
    private string? sharedPublicationVersionErrorMessage;

    public MainWindowViewModel()
        : this(new EngineHostApiClient())
    {
    }

    public MainWindowViewModel(IEngineHostApiClient apiClient)
        : this(new EngineHostHealthClient(apiClient), apiClient)
    {
    }

    public MainWindowViewModel(EngineHostHealthClient healthClient)
        : this(healthClient, new EngineHostApiClient())
    {
    }

    public MainWindowViewModel(
        EngineHostHealthClient healthClient,
        IEngineHostApiClient apiClient)
        : this(
            healthClient,
            apiClient,
            new EngineHostRuntimeEventStreamClient())
    {
    }

    public MainWindowViewModel(
        EngineHostHealthClient healthClient,
        IEngineHostApiClient apiClient,
        IEngineHostRuntimeEventStreamClient runtimeEventStreamClient,
        Func<CancellationToken, Task>? runtimeEventReconnectDelay = null,
        IConnectionSettingsStore? connectionSettingsStore = null)
    {
        _healthClient = healthClient;
        _apiClient = apiClient;
        _runtimeEventStreamClient = runtimeEventStreamClient;
        _runtimeEventReconnectDelay = runtimeEventReconnectDelay
            ?? (cancellationToken => Task.Delay(TimeSpan.FromSeconds(2), cancellationToken));
        _connectionSettingsStore = connectionSettingsStore ?? new FileConnectionSettingsStore();
    }

    public ObservableCollection<WorkflowListItemViewModel> Workflows { get; } = new();

    public ObservableCollection<WorkflowRunListItemViewModel> Runs { get; } = new();

    public ObservableCollection<NodeRunListItemViewModel> NodeRuns { get; } = new();

    public ObservableCollection<RuntimeEventListItemViewModel> RuntimeEvents { get; } = new();

    public ObservableCollection<RuntimeEventListItemViewModel> RuntimeEventLogEntries { get; } = new();

    public ObservableCollection<AuditEventListItemViewModel> AuditEvents { get; } = new();

    public ObservableCollection<TableRefListItemViewModel> TableRefs { get; } = new();

    public ObservableCollection<SharedPublicationListItemViewModel> SharedPublications { get; } =
        new();

    public ObservableCollection<SharedPublicationListItemViewModel> SharedPublicationVersions { get; } =
        new();

    public bool IsChecking => ConnectionStatus == ConnectionStatus.Connecting;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public bool HasWorkflowError => !string.IsNullOrWhiteSpace(WorkflowErrorMessage);

    public bool IsWorkflowBusy => IsLoadingWorkflows || IsStartingWorkflow;

    public bool HasLastStartedRun => !string.IsNullOrWhiteSpace(LastStartedRunId);

    public bool IsRunBusy => IsLoadingRuns || IsCancellingRun;

    public bool HasRunError => !string.IsNullOrWhiteSpace(RunErrorMessage);

    public bool IsNodeRunBusy => IsLoadingNodeRuns;

    public bool HasNodeRunError => !string.IsNullOrWhiteSpace(NodeRunErrorMessage);

    public bool HasRuntimeEventStreamError =>
        !string.IsNullOrWhiteSpace(RuntimeEventStreamErrorMessage);

    public bool HasRuntimeEvents => RuntimeEvents.Count > 0;

    public bool HasRuntimeEventLogError =>
        !string.IsNullOrWhiteSpace(RuntimeEventLogErrorMessage);

    public bool HasAuditEventLogError =>
        !string.IsNullOrWhiteSpace(AuditEventLogErrorMessage);

    public bool IsLogBusy => IsLoadingRuntimeEventLog || IsLoadingAuditEventLog;

    public bool HasTableRefError => !string.IsNullOrWhiteSpace(TableRefErrorMessage);

    public bool HasSharedPublicationError =>
        !string.IsNullOrWhiteSpace(SharedPublicationErrorMessage);

    public bool HasSharedPublicationVersionError =>
        !string.IsNullOrWhiteSpace(SharedPublicationVersionErrorMessage);

    public bool IsDataBusy =>
        IsLoadingTableRefs || IsLoadingSharedPublications || IsLoadingSharedPublicationVersions;

    public async Task LoadConnectionSettingsAsync(
        CancellationToken cancellationToken = default)
    {
        try
        {
            var settings = await _connectionSettingsStore.LoadAsync(cancellationToken);
            BaseUrl = settings.LastSuccessfulBaseUrl;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Connection settings were not loaded: {ex.Message}";
        }
    }

    private bool CanCheckConnection()
    {
        return ConnectionStatus != ConnectionStatus.Connecting;
    }

    private bool CanRefreshWorkflows()
    {
        return !IsWorkflowBusy;
    }

    private bool CanStartSelectedWorkflow()
    {
        return SelectedWorkflow is not null && !IsWorkflowBusy;
    }

    private bool CanRefreshRuns()
    {
        return !IsRunBusy;
    }

    private bool CanCancelSelectedRun()
    {
        return SelectedRun is not null && !IsRunBusy;
    }

    private bool CanRefreshNodeRuns()
    {
        return SelectedRun is not null && !IsNodeRunBusy;
    }

    private bool CanStartRuntimeEventStream()
    {
        return !IsRuntimeEventStreamRunning;
    }

    private bool CanStopRuntimeEventStream()
    {
        return IsRuntimeEventStreamRunning;
    }

    private bool CanRefreshRuntimeEventLog()
    {
        return !IsLoadingRuntimeEventLog;
    }

    private bool CanRefreshAuditEvents()
    {
        return !IsLoadingAuditEventLog;
    }

    private bool CanRefreshTableRefs()
    {
        return SelectedRun is not null && !IsLoadingTableRefs;
    }

    private bool CanRefreshSharedPublications()
    {
        return !IsLoadingSharedPublications;
    }

    private bool CanRefreshSharedPublicationVersions()
    {
        return !IsLoadingSharedPublicationVersions;
    }

    [RelayCommand(CanExecute = nameof(CanCheckConnection))]
    private async Task CheckConnectionAsync()
    {
        ConnectionStatus = ConnectionStatus.Connecting;
        StatusMessage = "Checking EngineHost...";
        ErrorMessage = null;

        var settings = new EngineHostConnectionSettings
        {
            BaseUrl = BaseUrl,
            Token = Token,
        };

        var result = await _healthClient.CheckAsync(settings);

        if (result.IsHealthy)
        {
            ConnectionStatus = ConnectionStatus.Connected;
            StatusMessage = result.Message;
            ErrorMessage = null;
            await SaveConnectionSettingsAsync(settings);
            return;
        }

        ConnectionStatus = ConnectionStatus.Error;
        StatusMessage = result.Message;
        ErrorMessage = result.ErrorMessage;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshWorkflows))]
    private async Task RefreshWorkflowsAsync()
    {
        IsLoadingWorkflows = true;
        WorkflowMessage = "Loading workflows...";
        WorkflowErrorMessage = null;

        var response = await _apiClient.ListWorkflowsAsync(
            BuildSettings(),
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            var previousWorkflowId = SelectedWorkflow?.WorkflowId;
            Workflows.Clear();
            foreach (var workflow in response.Data)
            {
                Workflows.Add(new WorkflowListItemViewModel(workflow));
            }

            SelectedWorkflow = Workflows.FirstOrDefault(
                workflow => workflow.WorkflowId == previousWorkflowId)
                ?? Workflows.FirstOrDefault();
            WorkflowMessage = $"Loaded {Workflows.Count} workflow(s).";
            IsLoadingWorkflows = false;
            return;
        }

        WorkflowMessage = "Workflow refresh failed.";
        WorkflowErrorMessage = DescribeError(response);
        IsLoadingWorkflows = false;
    }

    [RelayCommand(CanExecute = nameof(CanStartSelectedWorkflow))]
    private async Task StartSelectedWorkflowAsync()
    {
        if (SelectedWorkflow is null)
        {
            return;
        }

        IsStartingWorkflow = true;
        WorkflowMessage = $"Starting {SelectedWorkflow.Name}...";
        WorkflowErrorMessage = null;
        LastStartedRunId = null;
        LastStartedRunStatus = null;

        var response = await _apiClient.StartWorkflowRunAsync(
            BuildSettings(),
            SelectedWorkflow.WorkflowId,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            LastStartedRunId = response.Data.WorkflowRunId;
            LastStartedRunStatus = response.Data.Status;
            WorkflowMessage =
                $"Started run {response.Data.WorkflowRunId} ({response.Data.Status}).";
            IsStartingWorkflow = false;
            await LoadRunsAsync(response.Data.WorkflowRunId);
            return;
        }

        WorkflowMessage = "Workflow start failed.";
        WorkflowErrorMessage = DescribeError(response);
        IsStartingWorkflow = false;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshRuns))]
    private Task RefreshRunsAsync()
    {
        return LoadRunsAsync();
    }

    [RelayCommand(CanExecute = nameof(CanCancelSelectedRun))]
    private async Task CancelSelectedRunAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var workflowRunId = SelectedRun.WorkflowRunId;
        IsCancellingRun = true;
        RunMessage = $"Cancelling run {workflowRunId}...";
        RunErrorMessage = null;

        var response = await _apiClient.CancelRunAsync(
            BuildSettings(),
            workflowRunId,
            _shutdown.Token);

        IsCancellingRun = false;

        if (response.Ok)
        {
            var processStatus = response.Data?.Status;
            var cancelMessage = string.IsNullOrWhiteSpace(processStatus)
                ? $"Cancel requested for run {workflowRunId}."
                : $"Cancel requested for run {workflowRunId} ({processStatus}).";
            await LoadRunsAsync(workflowRunId);
            if (!HasRunError)
            {
                RunMessage = cancelMessage;
            }

            return;
        }

        RunMessage = "Run cancel failed.";
        RunErrorMessage = DescribeError(response);
    }

    [RelayCommand(CanExecute = nameof(CanRefreshNodeRuns))]
    private async Task RefreshNodeRunsAsync()
    {
        await LoadNodeRunsForSelectedRunAsync();
    }

    [RelayCommand(CanExecute = nameof(CanStartRuntimeEventStream))]
    private Task StartRuntimeEventStreamAsync()
    {
        try
        {
            _runtimeEventStreamClient.BuildEventsUri(BuildSettings());
        }
        catch (InvalidOperationException ex)
        {
            RuntimeEventStreamMessage = "Event stream configuration invalid.";
            RuntimeEventStreamErrorMessage = ex.Message;
            return Task.CompletedTask;
        }

        RuntimeEventStreamErrorMessage = null;
        RuntimeEventStreamMessage = "Connecting event stream...";
        RuntimeEvents.Clear();
        OnPropertyChanged(nameof(HasRuntimeEvents));
        LastRuntimeEventSequenceNumber = null;

        _runtimeEventStreamCancellation?.Cancel();
        _runtimeEventStreamCancellation?.Dispose();
        _runtimeEventStreamCancellation =
            CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        IsRuntimeEventStreamRunning = true;
        IsRuntimeEventStreamConnected = false;
        _runtimeEventStreamTask = RunRuntimeEventStreamLoopAsync(
            _runtimeEventStreamCancellation.Token);
        return Task.CompletedTask;
    }

    [RelayCommand(CanExecute = nameof(CanStopRuntimeEventStream))]
    private async Task StopRuntimeEventStreamAsync()
    {
        var cancellation = _runtimeEventStreamCancellation;
        var streamTask = _runtimeEventStreamTask;
        if (cancellation is null || streamTask is null)
        {
            return;
        }

        RuntimeEventStreamMessage = "Stopping event stream...";
        cancellation.Cancel();

        try
        {
            await streamTask;
        }
        catch (OperationCanceledException)
        {
        }

        RuntimeEventStreamMessage = "Event stream stopped.";
        RuntimeEventStreamErrorMessage = null;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshRuntimeEventLog))]
    private async Task RefreshRuntimeEventLogAsync()
    {
        if (!TryParseRuntimeEventLogFilters(out var afterSequenceNumber, out var limit, out var error))
        {
            RuntimeEventLogMessage = "Runtime event refresh rejected.";
            RuntimeEventLogErrorMessage = error;
            return;
        }

        IsLoadingRuntimeEventLog = true;
        RuntimeEventLogMessage = "Loading runtime events...";
        RuntimeEventLogErrorMessage = null;

        var response = await _apiClient.ListEventsAsync(
            BuildSettings(),
            afterSequenceNumber,
            NormalizeFilter(LogWorkflowRunIdFilter),
            NormalizeFilter(LogNodeRunIdFilter),
            NormalizeFilter(LogEventTypeFilter),
            limit,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            RuntimeEventLogEntries.Clear();
            foreach (var runtimeEvent in response.Data)
            {
                RuntimeEventLogEntries.Add(new RuntimeEventListItemViewModel(runtimeEvent));
            }

            RuntimeEventLogMessage =
                $"Loaded {RuntimeEventLogEntries.Count} runtime event(s).";
            IsLoadingRuntimeEventLog = false;
            return;
        }

        RuntimeEventLogMessage = "Runtime event refresh failed.";
        RuntimeEventLogErrorMessage = DescribeError(response);
        IsLoadingRuntimeEventLog = false;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshAuditEvents))]
    private async Task RefreshAuditEventsAsync()
    {
        IsLoadingAuditEventLog = true;
        AuditEventLogMessage = "Loading audit events...";
        AuditEventLogErrorMessage = null;

        var response = await _apiClient.ListAuditEventsAsync(
            BuildSettings(),
            NormalizeFilter(LogWorkflowRunIdFilter),
            NormalizeFilter(LogNodeRunIdFilter),
            NormalizeFilter(LogEventTypeFilter),
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            AuditEvents.Clear();
            foreach (var auditEvent in response.Data)
            {
                AuditEvents.Add(new AuditEventListItemViewModel(auditEvent));
            }

            AuditEventLogMessage = $"Loaded {AuditEvents.Count} audit event(s).";
            IsLoadingAuditEventLog = false;
            return;
        }

        AuditEventLogMessage = "Audit event refresh failed.";
        AuditEventLogErrorMessage = DescribeError(response);
        IsLoadingAuditEventLog = false;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshTableRefs))]
    private async Task RefreshTableRefsAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        IsLoadingTableRefs = true;
        TableRefMessage = $"Loading table refs for {SelectedRun.WorkflowRunId}...";
        TableRefErrorMessage = null;

        var response = await _apiClient.ListTableRefsAsync(
            BuildSettings(),
            SelectedRun.WorkflowRunId,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            TableRefs.Clear();
            foreach (var tableRef in response.Data)
            {
                TableRefs.Add(new TableRefListItemViewModel(tableRef));
            }

            TableRefMessage = $"Loaded {TableRefs.Count} table ref(s).";
            IsLoadingTableRefs = false;
            return;
        }

        TableRefMessage = "Table ref refresh failed.";
        TableRefErrorMessage = DescribeError(response);
        IsLoadingTableRefs = false;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSharedPublications))]
    private async Task RefreshSharedPublicationsAsync()
    {
        if (!TryParseLimit(
            SharedPublicationLimitFilter,
            "Shared publication limit",
            out var limit,
            out var error))
        {
            SharedPublicationMessage = "Shared publication refresh rejected.";
            SharedPublicationErrorMessage = error;
            return;
        }

        IsLoadingSharedPublications = true;
        SharedPublicationMessage = "Loading shared publications...";
        SharedPublicationErrorMessage = null;

        var response = await _apiClient.ListSharedPublicationsAsync(
            BuildSettings(),
            NormalizeFilter(SharedPublicationShareNameFilter),
            limit,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            var previousPublicationId = SelectedSharedPublication?.PublicationId;
            SharedPublications.Clear();
            foreach (var publication in response.Data)
            {
                SharedPublications.Add(new SharedPublicationListItemViewModel(publication));
            }

            SelectedSharedPublication = SharedPublications.FirstOrDefault(
                publication => publication.PublicationId == previousPublicationId)
                ?? SharedPublications.FirstOrDefault();
            SharedPublicationMessage =
                $"Loaded {SharedPublications.Count} shared publication(s).";
            IsLoadingSharedPublications = false;
            return;
        }

        SharedPublicationMessage = "Shared publication refresh failed.";
        SharedPublicationErrorMessage = DescribeError(response);
        IsLoadingSharedPublications = false;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSharedPublicationVersions))]
    private async Task RefreshSharedPublicationVersionsAsync()
    {
        var shareName = NormalizeFilter(SharedPublicationVersionShareNameFilter)
            ?? SelectedSharedPublication?.ShareName;
        if (string.IsNullOrWhiteSpace(shareName))
        {
            SharedPublicationVersionMessage = "Shared publication versions rejected.";
            SharedPublicationVersionErrorMessage =
                "Share name is required to load shared publication versions.";
            return;
        }

        if (!TryParseLimit(
            SharedPublicationVersionLimitFilter,
            "Shared publication version limit",
            out var limit,
            out var error))
        {
            SharedPublicationVersionMessage = "Shared publication versions rejected.";
            SharedPublicationVersionErrorMessage = error;
            return;
        }

        IsLoadingSharedPublicationVersions = true;
        SharedPublicationVersionMessage = $"Loading versions for {shareName}...";
        SharedPublicationVersionErrorMessage = null;

        var response = await _apiClient.ListSharedPublicationVersionsAsync(
            BuildSettings(),
            shareName,
            limit,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            SharedPublicationVersions.Clear();
            foreach (var publication in response.Data)
            {
                SharedPublicationVersions.Add(new SharedPublicationListItemViewModel(publication));
            }

            SharedPublicationVersionMessage =
                $"Loaded {SharedPublicationVersions.Count} version(s) for {shareName}.";
            IsLoadingSharedPublicationVersions = false;
            return;
        }

        SharedPublicationVersionMessage = "Shared publication versions refresh failed.";
        SharedPublicationVersionErrorMessage = DescribeError(response);
        IsLoadingSharedPublicationVersions = false;
    }

    private async Task LoadNodeRunsForSelectedRunAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        IsLoadingNodeRuns = true;
        NodeRunMessage = $"Loading nodes for {SelectedRun.WorkflowRunId}...";
        NodeRunErrorMessage = null;

        var response = await _apiClient.ListNodeRunsAsync(
            BuildSettings(),
            SelectedRun.WorkflowRunId,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            NodeRuns.Clear();
            foreach (var nodeRun in response.Data)
            {
                NodeRuns.Add(new NodeRunListItemViewModel(nodeRun));
            }

            NodeRunMessage = $"Loaded {NodeRuns.Count} node run(s).";
            IsLoadingNodeRuns = false;
            return;
        }

        NodeRunMessage = "Node status refresh failed.";
        NodeRunErrorMessage = DescribeError(response);
        IsLoadingNodeRuns = false;
    }

    private async Task RunRuntimeEventStreamLoopAsync(CancellationToken cancellationToken)
    {
        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    RuntimeEventStreamMessage = "Connecting event stream...";
                    RuntimeEventStreamErrorMessage = null;

                    await using var stream = await _runtimeEventStreamClient.ConnectAsync(
                        BuildSettings(),
                        cancellationToken);
                    IsRuntimeEventStreamConnected = true;
                    RuntimeEventStreamMessage = "Event stream connected.";
                    await RecoverRuntimeStateAsync(cancellationToken: cancellationToken);

                    while (!cancellationToken.IsCancellationRequested)
                    {
                        var runtimeEvent = await stream.ReadNextAsync(cancellationToken);
                        if (runtimeEvent is null)
                        {
                            IsRuntimeEventStreamConnected = false;
                            RuntimeEventStreamMessage =
                                "Event stream disconnected. Reconnecting...";
                            await RecoverRuntimeStateAsync(cancellationToken: cancellationToken);
                            break;
                        }

                        await AcceptRuntimeEventAsync(runtimeEvent, cancellationToken);
                    }
                }
                catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
                {
                    break;
                }
                catch (Exception ex)
                {
                    IsRuntimeEventStreamConnected = false;
                    RuntimeEventStreamMessage = "Event stream error. Reconnecting...";
                    RuntimeEventStreamErrorMessage = ex.Message;
                    await RecoverRuntimeStateAsync(cancellationToken: cancellationToken);
                }

                if (!cancellationToken.IsCancellationRequested)
                {
                    await _runtimeEventReconnectDelay(cancellationToken);
                }
            }
        }
        finally
        {
            IsRuntimeEventStreamConnected = false;
            IsRuntimeEventStreamRunning = false;
            if (_runtimeEventStreamCancellation?.Token == cancellationToken)
            {
                _runtimeEventStreamCancellation.Dispose();
                _runtimeEventStreamCancellation = null;
                _runtimeEventStreamTask = null;
            }
        }
    }

    private async Task AcceptRuntimeEventAsync(
        RuntimeEventDto runtimeEvent,
        CancellationToken cancellationToken)
    {
        RuntimeEvents.Insert(0, new RuntimeEventListItemViewModel(runtimeEvent));
        while (RuntimeEvents.Count > MaxRuntimeEvents)
        {
            RuntimeEvents.RemoveAt(RuntimeEvents.Count - 1);
        }

        OnPropertyChanged(nameof(HasRuntimeEvents));
        LastRuntimeEventSequenceNumber = runtimeEvent.SequenceNumber;
        RuntimeEventStreamMessage =
            $"Received {runtimeEvent.EventType} #{runtimeEvent.SequenceNumber}.";
        RuntimeEventStreamErrorMessage = null;

        await RecoverRuntimeStateAsync(
            runtimeEvent.WorkflowRunId,
            cancellationToken);
    }

    private async Task RecoverRuntimeStateAsync(
        string? selectWorkflowRunId = null,
        CancellationToken cancellationToken = default)
    {
        try
        {
            await LoadRunsAsync(selectWorkflowRunId);
            if (SelectedRun is not null)
            {
                await LoadNodeRunsForSelectedRunAsync();
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            RuntimeEventStreamErrorMessage = ex.Message;
        }
    }

    private async Task LoadRunsAsync(string? selectWorkflowRunId = null)
    {
        IsLoadingRuns = true;
        RunMessage = SelectedWorkflow is null
            ? "Loading runs..."
            : $"Loading runs for {SelectedWorkflow.Name}...";
        RunErrorMessage = null;

        var workflowId = SelectedWorkflow?.WorkflowId;
        var response = await _apiClient.ListRunsAsync(
            BuildSettings(),
            workflowId,
            cancellationToken: _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            var previousRunId = selectWorkflowRunId ?? SelectedRun?.WorkflowRunId;
            Runs.Clear();
            foreach (var run in response.Data)
            {
                Runs.Add(new WorkflowRunListItemViewModel(run));
            }

            SelectedRun = Runs.FirstOrDefault(run => run.WorkflowRunId == previousRunId)
                ?? Runs.FirstOrDefault();
            RunMessage = workflowId is null
                ? $"Loaded {Runs.Count} run(s)."
                : $"Loaded {Runs.Count} run(s) for {SelectedWorkflow?.Name}.";
            IsLoadingRuns = false;
            return;
        }

        RunMessage = "Run refresh failed.";
        RunErrorMessage = DescribeError(response);
        IsLoadingRuns = false;
    }

    private EngineHostConnectionSettings BuildSettings()
    {
        return new EngineHostConnectionSettings
        {
            BaseUrl = BaseUrl,
            Token = Token,
        };
    }

    private async Task SaveConnectionSettingsAsync(
        EngineHostConnectionSettings settings)
    {
        try
        {
            await _connectionSettingsStore.SaveAsync(
                PersistedConnectionSettings.FromBaseUrl(settings.BaseUrl),
                _shutdown.Token);
        }
        catch (OperationCanceledException) when (_shutdown.Token.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Connection settings were not saved: {ex.Message}";
        }
    }

    private static string DescribeError<TData>(ApiResponseEnvelope<TData> response)
    {
        if (response.Error is null)
        {
            return "EngineHost response did not include data.";
        }

        return $"{response.Error.ErrorCode}: {response.Error.Message}";
    }

    private bool TryParseRuntimeEventLogFilters(
        out long? afterSequenceNumber,
        out int limit,
        out string? error)
    {
        afterSequenceNumber = null;
        limit = 100;
        error = null;

        var afterSequenceNumberText = NormalizeFilter(RuntimeEventAfterSequenceNumberFilter);
        if (afterSequenceNumberText is not null)
        {
            if (!long.TryParse(afterSequenceNumberText, out var parsedAfterSequenceNumber)
                || parsedAfterSequenceNumber < 0)
            {
                error = "After sequence number must be a non-negative integer.";
                return false;
            }

            afterSequenceNumber = parsedAfterSequenceNumber;
        }

        var limitText = NormalizeFilter(RuntimeEventLimitFilter);
        if (limitText is null)
        {
            return true;
        }

        if (!int.TryParse(limitText, out var parsedLimit)
            || parsedLimit is < 1 or > 1000)
        {
            error = "Runtime event limit must be between 1 and 1000.";
            return false;
        }

        limit = parsedLimit;
        return true;
    }

    private static bool TryParseLimit(
        string limitFilter,
        string label,
        out int limit,
        out string? error)
    {
        limit = 100;
        error = null;

        var limitText = NormalizeFilter(limitFilter);
        if (limitText is null)
        {
            return true;
        }

        if (!int.TryParse(limitText, out var parsedLimit)
            || parsedLimit is < 1 or > 1000)
        {
            error = $"{label} must be between 1 and 1000.";
            return false;
        }

        limit = parsedLimit;
        return true;
    }

    private static string? NormalizeFilter(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }

    partial void OnConnectionStatusChanged(ConnectionStatus value)
    {
        OnPropertyChanged(nameof(IsChecking));
        CheckConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }

    partial void OnIsLoadingWorkflowsChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnIsStartingWorkflowChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnSelectedWorkflowChanged(WorkflowListItemViewModel? value)
    {
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        Runs.Clear();
        SelectedRun = null;
        RunMessage = value is null
            ? "No workflow selected. Refresh runs will load all runs."
            : $"Selected {value.Name}. Refresh runs to load matching runs.";
        RunErrorMessage = null;
    }

    partial void OnWorkflowErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasWorkflowError));
    }

    partial void OnLastStartedRunIdChanged(string? value)
    {
        OnPropertyChanged(nameof(HasLastStartedRun));
    }

    partial void OnIsLoadingRunsChanged(bool value)
    {
        NotifyRunCommandStateChanged();
    }

    partial void OnIsCancellingRunChanged(bool value)
    {
        NotifyRunCommandStateChanged();
    }

    partial void OnSelectedRunChanged(WorkflowRunListItemViewModel? value)
    {
        NodeRuns.Clear();
        TableRefs.Clear();
        NodeRunMessage = value is null
            ? "Select a run to load node status."
            : $"Selected run {value.WorkflowRunId}. Refresh nodes to load status.";
        NodeRunErrorMessage = null;
        TableRefMessage = value is null
            ? "Select a run to load table refs."
            : $"Selected run {value.WorkflowRunId}. Refresh table refs to load data outputs.";
        TableRefErrorMessage = null;
        CancelSelectedRunCommand.NotifyCanExecuteChanged();
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
    }

    partial void OnRunErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRunError));
    }

    partial void OnIsLoadingNodeRunsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsNodeRunBusy));
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
    }

    partial void OnNodeRunErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasNodeRunError));
    }

    partial void OnIsRuntimeEventStreamRunningChanged(bool value)
    {
        StartRuntimeEventStreamCommand.NotifyCanExecuteChanged();
        StopRuntimeEventStreamCommand.NotifyCanExecuteChanged();
    }

    partial void OnRuntimeEventStreamErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeEventStreamError));
    }

    partial void OnIsLoadingRuntimeEventLogChanged(bool value)
    {
        OnPropertyChanged(nameof(IsLogBusy));
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
    }

    partial void OnRuntimeEventLogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeEventLogError));
    }

    partial void OnIsLoadingAuditEventLogChanged(bool value)
    {
        OnPropertyChanged(nameof(IsLogBusy));
        RefreshAuditEventsCommand.NotifyCanExecuteChanged();
    }

    partial void OnAuditEventLogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasAuditEventLogError));
    }

    partial void OnIsLoadingTableRefsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataBusy));
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
    }

    partial void OnTableRefErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasTableRefError));
    }

    partial void OnIsLoadingSharedPublicationsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataBusy));
        RefreshSharedPublicationsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedSharedPublicationChanged(SharedPublicationListItemViewModel? value)
    {
        if (value is not null)
        {
            SharedPublicationVersionShareNameFilter = value.ShareName;
        }
    }

    partial void OnSharedPublicationErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasSharedPublicationError));
    }

    partial void OnIsLoadingSharedPublicationVersionsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataBusy));
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSharedPublicationVersionErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasSharedPublicationVersionError));
    }

    private void NotifyWorkflowCommandStateChanged()
    {
        OnPropertyChanged(nameof(IsWorkflowBusy));
        RefreshWorkflowsCommand.NotifyCanExecuteChanged();
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
    }

    private void NotifyRunCommandStateChanged()
    {
        OnPropertyChanged(nameof(IsRunBusy));
        RefreshRunsCommand.NotifyCanExecuteChanged();
        CancelSelectedRunCommand.NotifyCanExecuteChanged();
    }
}
