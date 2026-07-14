using Avalonia_UI.Api;
using Avalonia_UI.Services;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public NodeRunMonitorViewModel NodeRunMonitor { get; private set; } = null!;

    private void InitializeNodeRunMonitor(IEngineHostApiClient apiClient)
    {
        NodeRunMonitor = new NodeRunMonitorViewModel(
            new RunTableDirectoryService(apiClient),
            T,
            DisplayTextFormatter);
        RefreshNodeRunMonitorContext();
    }

    private void RefreshNodeRunMonitorContext()
    {
        if (NodeRunMonitor is null)
        {
            return;
        }

        _ = NodeRunMonitor.SelectRunAsync(
            BuildSettings(),
            SelectedRun?.WorkflowRunId,
            CanUseEngineActions);
    }
}
