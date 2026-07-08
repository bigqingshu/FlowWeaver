using System;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
