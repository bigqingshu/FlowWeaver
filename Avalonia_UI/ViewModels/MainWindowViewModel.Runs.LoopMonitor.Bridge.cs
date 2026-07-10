using Avalonia_UI.Api;
using Avalonia_UI.Services;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private RunMetadataCache runMetadataCache = null!;

    public RunLoopMonitorViewModel RunLoopMonitor { get; private set; } = null!;

    private void InitializeRunLoopMonitor(IEngineHostApiClient apiClient)
    {
        var loopRunQueryService = new LoopRunQueryService(apiClient);
        runMetadataCache = new RunMetadataCache(
            new RunTableDirectoryService(apiClient),
            loopRunQueryService);
        RunLoopMonitor = new RunLoopMonitorViewModel(
            loopRunQueryService,
            runMetadataCache,
            T);
    }
}
