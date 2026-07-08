using System;
using System.Collections.ObjectModel;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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

    partial void OnConnectionStatusChanged(ConnectionStatus value)
    {
        OnPropertyChanged(nameof(IsChecking));
        NotifyEngineActionStateChanged();
        CheckConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnTokenChanged(string value)
    {
        IsAuthenticationFailed = false;
        InvalidateNodeDefinitionCatalogCacheState();
        NotifyEngineActionStateChanged();
    }

    partial void OnBaseUrlChanged(string value)
    {
        IsAuthenticationFailed = false;
        InvalidateNodeDefinitionCatalogCacheState();
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
}
