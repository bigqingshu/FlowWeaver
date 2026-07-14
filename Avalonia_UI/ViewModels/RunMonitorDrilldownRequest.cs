namespace Avalonia_UI.ViewModels;

public enum RunMonitorDrilldownDestination
{
    Tables,
    Preview,
    Logs,
}

public sealed record RunMonitorDrilldownRequest(
    RunMonitorDrilldownDestination Destination,
    string WorkflowRunId,
    string? NodeRunId = null);
