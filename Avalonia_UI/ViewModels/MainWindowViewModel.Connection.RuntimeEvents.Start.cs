using System;
using System.Threading;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
