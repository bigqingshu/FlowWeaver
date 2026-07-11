using Avalonia_UI.Services;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public bool CanOpenSelectedRunRuntimeOptions =>
        CanUseEngineActions && SelectedRun is not null;

    public string CurrentRunRuntimeOptionsOpenText =>
        T("run_runtime_options.open");

    public WorkflowRunRuntimeOptionsViewModel? CreateSelectedRunRuntimeOptionsViewModel()
    {
        var run = SelectedRun;
        if (!CanOpenSelectedRunRuntimeOptions || run is null)
        {
            return null;
        }

        return new WorkflowRunRuntimeOptionsViewModel(
            new WorkflowRunRuntimeOptionsService(_apiClient),
            BuildSettings(),
            run.WorkflowRunId,
            run.Status,
            run.RunMode,
            run.TriggerSource,
            _localizationService);
    }
}
