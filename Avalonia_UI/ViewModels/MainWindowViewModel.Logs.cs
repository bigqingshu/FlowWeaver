using System;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int runtimeEventLogLoadVersion;

    [ObservableProperty]
    private string logWorkflowRunIdFilter = string.Empty;

    [ObservableProperty]
    private string logNodeRunIdFilter = string.Empty;

    [ObservableProperty]
    private string logEventTypeFilter = string.Empty;

    [ObservableProperty]
    private string runtimeEventAfterSequenceNumberFilter = string.Empty;

    [ObservableProperty]
    private string runtimeEventLimitFilter = "100";

    [ObservableProperty]
    private bool isLoadingRuntimeEventLog;

    [ObservableProperty]
    private string runtimeEventLogMessage = "No runtime events loaded.";

    [ObservableProperty]
    private string? runtimeEventLogErrorMessage;

    public ObservableCollection<RuntimeEventListItemViewModel> RuntimeEventLogEntries { get; } = new();

    public bool HasRuntimeEventLogError =>
        !string.IsNullOrWhiteSpace(RuntimeEventLogErrorMessage);

    public bool IsLogBusy => IsLoadingRuntimeEventLog;

    public string WorkflowRunFilterText => T("logs.workflow_run");

    public string RunIdWatermarkText => T("logs.run_id_watermark");

    public string NodeRunFilterText => T("logs.node_run");

    public string NodeRunIdWatermarkText => T("logs.node_run_id_watermark");

    public string EventTypeFilterText => T("logs.event_type");

    public string AfterFilterText => T("logs.after");

    public string SequenceWatermarkText => T("logs.sequence_watermark");

    public string RuntimeText => T("logs.runtime");

    public string LimitText => T("common.limit");

    public string RuntimeEventsSectionText => T("logs.runtime_events");

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

    partial void OnIsLoadingRuntimeEventLogChanged(bool value)
    {
        OnPropertyChanged(nameof(IsLogBusy));
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
    }

    partial void OnRuntimeEventLogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeEventLogError));
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
