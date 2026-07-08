namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryParseRuntimeEventLogFilters(
        out long? afterSequenceNumber,
        out int limit,
        out string? error)
    {
        afterSequenceNumber = null;
        limit = 100;
        error = null;

        var afterSequenceNumberText = NormalizeFilter(RuntimeEventAfterSequenceNumberFilter);
        if (afterSequenceNumberText is not null)
        {
            if (!long.TryParse(afterSequenceNumberText, out var parsedAfterSequenceNumber)
                || parsedAfterSequenceNumber < 0)
            {
                error = T("logs.after_sequence_invalid");
                return false;
            }

            afterSequenceNumber = parsedAfterSequenceNumber;
        }

        var limitText = NormalizeFilter(RuntimeEventLimitFilter);
        if (limitText is null)
        {
            return true;
        }

        if (!int.TryParse(limitText, out var parsedLimit)
            || parsedLimit is < 1 or > 1000)
        {
            error = T("logs.runtime_event_limit_invalid");
            return false;
        }

        limit = parsedLimit;
        return true;
    }

    partial void OnLogWorkflowRunIdFilterChanged(string value)
    {
        InvalidateLogLoads();
    }

    partial void OnLogNodeRunIdFilterChanged(string value)
    {
        InvalidateLogLoads();
    }

    partial void OnLogEventTypeFilterChanged(string value)
    {
        InvalidateLogLoads();
    }

    private void InvalidateLogLoads()
    {
        runtimeEventLogLoadVersion++;
        IsLoadingRuntimeEventLog = false;
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
    }
}
