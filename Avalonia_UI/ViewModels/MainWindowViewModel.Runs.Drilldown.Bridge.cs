using System;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private Task pendingRunMonitorDrilldownTask = Task.CompletedTask;

    [ObservableProperty]
    private string? runTableNodeRunIdFilter;

    public Task WaitForPendingRunMonitorDrilldownAsync()
    {
        return pendingRunMonitorDrilldownTask;
    }

    private void OnRunMonitorDrilldownRequested(RunMonitorDrilldownRequest request)
    {
        pendingRunMonitorDrilldownTask = NavigateFromRunMonitorAsync(request);
    }

    private async Task NavigateFromRunMonitorAsync(RunMonitorDrilldownRequest request)
    {
        if (!string.Equals(
                SelectedRun?.WorkflowRunId,
                request.WorkflowRunId,
                StringComparison.Ordinal))
        {
            return;
        }

        switch (request.Destination)
        {
            case RunMonitorDrilldownDestination.Tables:
                RunTableNodeRunIdFilter = request.NodeRunId;
                SelectedShellPageKey = ShellPageKey.Data;
                await RefreshTableRefsAsync();
                break;
            case RunMonitorDrilldownDestination.Preview:
                RunTableNodeRunIdFilter = request.NodeRunId;
                SelectedShellPageKey = ShellPageKey.DataPreview;
                await RefreshTableRefsAsync();
                break;
            case RunMonitorDrilldownDestination.Logs:
                LogWorkflowRunIdFilter = request.WorkflowRunId;
                LogNodeRunIdFilter = request.NodeRunId ?? string.Empty;
                SelectedShellPageKey = ShellPageKey.Logs;
                await RefreshRuntimeEventLogAsync();
                break;
            default:
                throw new ArgumentOutOfRangeException(
                    nameof(request),
                    request.Destination,
                    "Unknown run monitor drilldown destination.");
        }
    }
}
