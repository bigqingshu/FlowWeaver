using CommunityToolkit.Mvvm.ComponentModel;

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

    partial void OnIsLoadingRuntimeEventLogChanged(bool value)
    {
        OnPropertyChanged(nameof(IsLogBusy));
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
    }

    partial void OnRuntimeEventLogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeEventLogError));
    }
}
