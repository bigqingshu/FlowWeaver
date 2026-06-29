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
    private readonly IEngineHostApiClient _apiClient;
    private readonly EngineHostHealthClient _healthClient;

    private readonly CancellationTokenSource _shutdown = new();

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
    {
        _healthClient = healthClient;
        _apiClient = apiClient;
    }

    public ObservableCollection<WorkflowListItemViewModel> Workflows { get; } = new();

    public ObservableCollection<WorkflowRunListItemViewModel> Runs { get; } = new();

    public ObservableCollection<NodeRunListItemViewModel> NodeRuns { get; } = new();

    public bool IsChecking => ConnectionStatus == ConnectionStatus.Connecting;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public bool HasWorkflowError => !string.IsNullOrWhiteSpace(WorkflowErrorMessage);

    public bool IsWorkflowBusy => IsLoadingWorkflows || IsStartingWorkflow;

    public bool HasLastStartedRun => !string.IsNullOrWhiteSpace(LastStartedRunId);

    public bool IsRunBusy => IsLoadingRuns || IsCancellingRun;

    public bool HasRunError => !string.IsNullOrWhiteSpace(RunErrorMessage);

    public bool IsNodeRunBusy => IsLoadingNodeRuns;

    public bool HasNodeRunError => !string.IsNullOrWhiteSpace(NodeRunErrorMessage);

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

    private static string DescribeError<TData>(ApiResponseEnvelope<TData> response)
    {
        if (response.Error is null)
        {
            return "EngineHost response did not include data.";
        }

        return $"{response.Error.ErrorCode}: {response.Error.Message}";
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
        NodeRunMessage = value is null
            ? "Select a run to load node status."
            : $"Selected run {value.WorkflowRunId}. Refresh nodes to load status.";
        NodeRunErrorMessage = null;
        CancelSelectedRunCommand.NotifyCanExecuteChanged();
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
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
