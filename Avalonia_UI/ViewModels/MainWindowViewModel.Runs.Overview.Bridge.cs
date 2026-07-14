using Avalonia_UI.Api;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public RunOverviewViewModel RunOverview { get; private set; } = null!;

    [ObservableProperty]
    private int selectedRunMonitorTabIndex;

    private void InitializeRunOverview(IEngineHostApiClient apiClient)
    {
        RunOverview = new RunOverviewViewModel(
            new RunReviewService(apiClient),
            T,
            DisplayTextFormatter);
        RunOverview.SetActive(SelectedRunMonitorTabIndex == 0);
        RefreshRunOverviewContext();
    }

    private void RefreshRunOverviewContext()
    {
        if (RunOverview is null)
        {
            return;
        }

        RunOverview.SetContext(
            BuildSettings(),
            SelectedRun?.WorkflowRunId,
            CanUseEngineActions);
    }

    partial void OnSelectedRunMonitorTabIndexChanged(int value)
    {
        RunOverview?.SetActive(value == 0);
    }
}
