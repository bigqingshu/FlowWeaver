using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshRuns()
    {
        return CanUseEngineActions && !IsRunBusy;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshRuns))]
    private Task RefreshRunsAsync()
    {
        return LoadRunsAsync();
    }

    private async Task LoadRunsAsync(
        string? selectWorkflowRunId = null,
        bool allowWhenActionsDisabled = false)
    {
        RefreshBackgroundRunManagementContext();
        await BackgroundRunManagement.LoadPageAsync(
            selectWorkflowRunId,
            resetOffset: selectWorkflowRunId is not null,
            allowWhenActionsDisabled: allowWhenActionsDisabled);
        SelectedRun = BackgroundRunManagement.SelectedRun;
        if (!BackgroundRunManagement.HasError)
        {
            RunMessage = SelectedWorkflow is null
                ? F("format.loaded_runs", Runs.Count)
                : F("format.loaded_runs_for", Runs.Count, SelectedWorkflow.Name);
        }
    }

}
