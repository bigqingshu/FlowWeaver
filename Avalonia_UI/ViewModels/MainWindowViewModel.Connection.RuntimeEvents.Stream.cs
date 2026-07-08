using System;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Services;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private const int MaxRuntimeEvents = 50;

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
}
