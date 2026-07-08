using System;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private readonly IEngineHostRuntimeEventStreamClient _runtimeEventStreamClient;
    private readonly Func<CancellationToken, Task> _runtimeEventReconnectDelay;

    private CancellationTokenSource? _runtimeEventStreamCancellation;
    private Task? _runtimeEventStreamTask;
    private bool runtimeEventStreamAutoConnect;

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
}
