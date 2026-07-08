using System;
using System.Threading;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanStartRuntimeEventStream()
    {
        return !IsRuntimeEventStreamRunning && !string.IsNullOrWhiteSpace(BaseUrl);
    }

    private bool CanStopRuntimeEventStream()
    {
        return IsRuntimeEventStreamRunning;
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
