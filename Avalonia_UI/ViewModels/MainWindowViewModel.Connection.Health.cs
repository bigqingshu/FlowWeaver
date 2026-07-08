using System;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanCheckConnection()
    {
        return !string.IsNullOrWhiteSpace(BaseUrl)
            && ConnectionStatus != ConnectionStatus.Connecting;
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
}
