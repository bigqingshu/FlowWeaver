using System;
using System.Collections.ObjectModel;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private const int MaxRuntimeEvents = 50;

    private readonly EngineHostHealthClient _healthClient;
    private readonly IEngineHostRuntimeEventStreamClient _runtimeEventStreamClient;
    private readonly Func<CancellationToken, Task> _runtimeEventReconnectDelay;
    private readonly IConnectionSettingsStore _connectionSettingsStore;

    private CancellationTokenSource? _runtimeEventStreamCancellation;
    private Task? _runtimeEventStreamTask;
    private bool runtimeEventStreamAutoConnect;

    [ObservableProperty]
    private string baseUrl = EngineHostConnectionSettings.DefaultBaseUrl;

    [ObservableProperty]
    private string token = string.Empty;

    [ObservableProperty]
    private ConnectionStatus connectionStatus = ConnectionStatus.Disconnected;

    [ObservableProperty]
    private bool isAuthenticationFailed;

    [ObservableProperty]
    private string statusMessage = "Disconnected.";

    [ObservableProperty]
    private string? errorMessage;

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

    public bool CanUseEngineActions =>
        ConnectionStatus == ConnectionStatus.Connected
        && !string.IsNullOrWhiteSpace(BaseUrl)
        && !string.IsNullOrWhiteSpace(Token)
        && !IsAuthenticationFailed;

    public ObservableCollection<RuntimeEventListItemViewModel> RuntimeEvents { get; } = new();

    public bool IsChecking => ConnectionStatus == ConnectionStatus.Connecting;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public bool HasRuntimeEventStreamError =>
        !string.IsNullOrWhiteSpace(RuntimeEventStreamErrorMessage);

    public bool HasRuntimeEvents => RuntimeEvents.Count > 0;

    public string ConnectionBaseUrlText => T("connection.base_url");

    public string ConnectionTokenText => T("connection.token");

    public string ConnectionStatusText => T("connection.status");

    public string ConnectionEventsText => T("connection.events");

    public string CheckConnectionText => T("connection.check");

    public string StreamText => T("connection.stream");

    public string StopText => T("connection.stop");

    public async Task LoadConnectionSettingsAsync(
        CancellationToken cancellationToken = default)
    {
        await TryLoadConnectionSettingsAsync(cancellationToken);
    }

    public async Task LoadConnectionSettingsAndCheckConnectionAsync(
        CancellationToken cancellationToken = default)
    {
        var loaded = await TryLoadConnectionSettingsAsync(cancellationToken);
        if (!loaded || !CanCheckConnection())
        {
            return;
        }

        await CheckConnectionCoreAsync(cancellationToken);
        if (ConnectionStatus == ConnectionStatus.Connected
            && runtimeEventStreamAutoConnect
            && !string.IsNullOrWhiteSpace(Token)
            && CanStartRuntimeEventStream())
        {
            await StartRuntimeEventStreamAsync();
        }
    }

    private async Task<bool> TryLoadConnectionSettingsAsync(
        CancellationToken cancellationToken)
    {
        try
        {
            var settings = await _connectionSettingsStore.LoadAsync(cancellationToken);
            BaseUrl = settings.LastSuccessfulBaseUrl;
            Token = settings.Token;
            runtimeEventStreamAutoConnect = settings.RuntimeEventStreamAutoConnect;
            return true;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            ErrorMessage = F("format.connection_settings_load_failed", ex.Message);
            return false;
        }
    }

    private bool CanCheckConnection()
    {
        return !string.IsNullOrWhiteSpace(BaseUrl)
            && ConnectionStatus != ConnectionStatus.Connecting;
    }

    private bool CanStartRuntimeEventStream()
    {
        return !IsRuntimeEventStreamRunning && !string.IsNullOrWhiteSpace(BaseUrl);
    }

    private bool CanStopRuntimeEventStream()
    {
        return IsRuntimeEventStreamRunning;
    }

    [RelayCommand(CanExecute = nameof(CanCheckConnection))]
    private async Task CheckConnectionAsync()
    {
        await CheckConnectionCoreAsync(_shutdown.Token);
    }

    private async Task CheckConnectionCoreAsync(
        CancellationToken cancellationToken)
    {
        ConnectionStatus = ConnectionStatus.Connecting;
        StatusMessage = T("status.checking_enginehost");
        ErrorMessage = null;

        var settings = new EngineHostConnectionSettings
        {
            BaseUrl = BaseUrl,
            Token = Token,
        };

        var result = await _healthClient.CheckAsync(settings, cancellationToken);

        if (result.IsHealthy)
        {
            ConnectionStatus = ConnectionStatus.Connected;
            StatusMessage = LocalizeHealthStatusMessage(result);
            ErrorMessage = null;
            await SaveConnectionSettingsAsync(settings);
            await RefreshNodeDefinitionsAfterHealthyConnectionAsync();
            await RefreshWorkflowsAfterHealthyConnectionAsync();
            ShowConnectionNotification(UiNotificationKind.Success);
            return;
        }

        ConnectionStatus = ConnectionStatus.Error;
        StatusMessage = LocalizeHealthStatusMessage(result);
        ErrorMessage = LocalizeHealthErrorMessage(result.ErrorMessage);
        ShowConnectionNotification(UiNotificationKind.Error);
    }

    [RelayCommand(CanExecute = nameof(CanStartRuntimeEventStream))]
    private async Task StartRuntimeEventStreamAsync()
    {
        var settings = BuildSettings();
        try
        {
            _runtimeEventStreamClient.BuildEventsUri(settings);
        }
        catch (InvalidOperationException ex)
        {
            RuntimeEventStreamMessage = T("events.stream_config_invalid");
            RuntimeEventStreamErrorMessage = ex.Message;
            return;
        }

        runtimeEventStreamAutoConnect = true;
        await SaveConnectionSettingsAsync(settings);
        RuntimeEventStreamErrorMessage = null;
        RuntimeEventStreamMessage = T("events.stream_connecting");
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

        RuntimeEventStreamMessage = T("events.stream_stopping");
        cancellation.Cancel();

        try
        {
            await streamTask;
        }
        catch (OperationCanceledException)
        {
        }

        RuntimeEventStreamMessage = T("events.stream_stopped");
        RuntimeEventStreamErrorMessage = null;
        runtimeEventStreamAutoConnect = false;
        await SaveConnectionSettingsAsync(BuildSettings());
    }

    private async Task RunRuntimeEventStreamLoopAsync(CancellationToken cancellationToken)
    {
        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    RuntimeEventStreamMessage = T("events.stream_connecting");
                    RuntimeEventStreamErrorMessage = null;

                    await using var stream = await _runtimeEventStreamClient.ConnectAsync(
                        BuildSettings(),
                        cancellationToken);
                    IsRuntimeEventStreamConnected = true;
                    RuntimeEventStreamMessage = T("events.stream_connected");
                    await RecoverRuntimeStateAsync(cancellationToken: cancellationToken);

                    while (!cancellationToken.IsCancellationRequested)
                    {
                        var runtimeEvent = await stream.ReadNextAsync(cancellationToken);
                        if (runtimeEvent is null)
                        {
                            IsRuntimeEventStreamConnected = false;
                            RuntimeEventStreamMessage =
                                T("events.stream_disconnected_reconnecting");
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
                    RuntimeEventStreamMessage = T("events.stream_error_reconnecting");
                    RuntimeEventStreamErrorMessage =
                        F(
                            "format.events.stream_connection_failed",
                            EngineHostConnectionDiagnostics.RedactToken(ex.Message));
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
        AddRecentRuntimeEvent(runtimeEvent);
        while (RuntimeEvents.Count > MaxRuntimeEvents)
        {
            RuntimeEvents.RemoveAt(RuntimeEvents.Count - 1);
        }

        OnPropertyChanged(nameof(HasRuntimeEvents));
        LastRuntimeEventSequenceNumber = runtimeEvent.SequenceNumber;
        RuntimeEventStreamMessage =
            F(
                "format.received_runtime_event",
                runtimeEvent.EventType,
                runtimeEvent.SequenceNumber);
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
                PersistedConnectionSettings.FromBaseUrl(
                    settings.BaseUrl,
                    settings.Token,
                    runtimeEventStreamAutoConnect: runtimeEventStreamAutoConnect),
                _shutdown.Token);
        }
        catch (OperationCanceledException) when (_shutdown.Token.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            ErrorMessage = F("format.connection_settings_save_failed", ex.Message);
        }
    }

    private string DescribeError<TData>(ApiResponseEnvelope<TData> response)
    {
        if (response.Error is null)
        {
            return T("diagnostics.response_missing_data");
        }

        if (response.Error.ErrorCode is "TOKEN_REQUIRED" or "UNAUTHORIZED")
        {
            IsAuthenticationFailed = true;
        }

        return response.Error.ErrorCode switch
        {
            "TOKEN_REQUIRED" => T("diagnostics.token_required"),
            "UNAUTHORIZED" => T("diagnostics.token_invalid"),
            "INVALID_BASE_URL" => F(
                "format.diagnostics.invalid_base_url",
                response.Error.Message),
            "REQUEST_TIMEOUT" => T("diagnostics.request_timeout"),
            "REQUEST_FAILED" => F(
                "format.diagnostics.request_failed",
                response.Error.Message),
            "WORKFLOW_VALIDATION_FAILED" =>
                FormatWorkflowValidationErrorDetails(response.Error)
                ?? $"{response.Error.ErrorCode}: {response.Error.Message}",
            _ => $"{response.Error.ErrorCode}: {response.Error.Message}",
        };
    }

    private static string? FormatWorkflowValidationErrorDetails(ApiErrorDto error)
    {
        if (error.Details.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null)
        {
            return null;
        }

        try
        {
            var validation = error.Details.Deserialize<WorkflowValidationResultDto>(
                FlowWeaverJson.Options);
            return validation is null ? null : FormatValidationIssues(validation);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private string LocalizeHealthStatusMessage(EngineHostHealthCheckResult result)
    {
        if (result.IsHealthy)
        {
            return T("connection.health_check_passed");
        }

        return string.Equals(result.Message, "Connection failed.", StringComparison.Ordinal)
            ? T("connection.failed")
            : result.Message;
    }

    private string? LocalizeHealthErrorMessage(string? message)
    {
        return message switch
        {
            null => null,
            "Connection timed out." => T("connection.timed_out"),
            "EngineHost health response was not recognized." =>
                T("connection.health_response_unrecognized"),
            "EngineHost base URL is required." => T("connection.base_url_required"),
            "EngineHost base URL must be an absolute URL." => T("connection.base_url_absolute"),
            "EngineHost base URL must use HTTP or HTTPS." => T("connection.base_url_http_https"),
            _ => message,
        };
    }

    partial void OnConnectionStatusChanged(ConnectionStatus value)
    {
        OnPropertyChanged(nameof(IsChecking));
        NotifyEngineActionStateChanged();
        CheckConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnTokenChanged(string value)
    {
        IsAuthenticationFailed = false;
        NotifyEngineActionStateChanged();
    }

    partial void OnBaseUrlChanged(string value)
    {
        IsAuthenticationFailed = false;
        NotifyEngineActionStateChanged();
        CheckConnectionCommand.NotifyCanExecuteChanged();
        StartRuntimeEventStreamCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsRuntimeEventStreamConnectedChanged(bool value)
    {
        NotifyEngineActionStateChanged();
    }

    partial void OnIsAuthenticationFailedChanged(bool value)
    {
        NotifyEngineActionStateChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
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
}
