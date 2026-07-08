using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshRuntimeEventLog()
    {
        return CanUseEngineActions && !IsLoadingRuntimeEventLog;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshRuntimeEventLog), AllowConcurrentExecutions = true)]
    private async Task RefreshRuntimeEventLogAsync()
    {
        if (!TryParseRuntimeEventLogFilters(out var afterSequenceNumber, out var limit, out var error))
        {
            RuntimeEventLogMessage = T("logs.runtime_refresh_rejected");
            RuntimeEventLogErrorMessage = error;
            return;
        }

        var requestVersion = ++runtimeEventLogLoadVersion;
        IsLoadingRuntimeEventLog = true;
        RuntimeEventLogMessage = T("logs.loading_runtime_events");
        RuntimeEventLogErrorMessage = null;

        try
        {
            var response = await _apiClient.ListEventsAsync(
                BuildSettings(),
                afterSequenceNumber,
                NormalizeFilter(LogWorkflowRunIdFilter),
                NormalizeFilter(LogNodeRunIdFilter),
                NormalizeFilter(LogEventTypeFilter),
                limit,
                _shutdown.Token);

            if (requestVersion != runtimeEventLogLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                RuntimeEventLogEntries.Clear();
                foreach (var runtimeEvent in response.Data)
                {
                    RuntimeEventLogEntries.Add(new RuntimeEventListItemViewModel(runtimeEvent));
                }

                RuntimeEventLogMessage =
                    F("format.loaded_runtime_events", RuntimeEventLogEntries.Count);
                return;
            }

            RuntimeEventLogMessage = T("logs.runtime_refresh_failed");
            RuntimeEventLogErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == runtimeEventLogLoadVersion)
            {
                IsLoadingRuntimeEventLog = false;
            }
        }
    }
}
