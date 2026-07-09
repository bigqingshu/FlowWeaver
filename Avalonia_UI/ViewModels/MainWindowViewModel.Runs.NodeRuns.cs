using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshNodeRuns()
    {
        return CanUseEngineActions && SelectedRun is not null && !IsNodeRunBusy;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshNodeRuns))]
    private async Task RefreshNodeRunsAsync()
    {
        await LoadNodeRunsForSelectedRunAsync();
    }

    private async Task LoadNodeRunsForSelectedRunAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestVersion = ++nodeRunsLoadVersion;
        IsLoadingNodeRuns = true;
        NodeRunMessage = F("format.loading_nodes_for", requestedRunId);
        NodeRunErrorMessage = null;

        try
        {
            var response = await _apiClient.ListNodeRunsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (
                SelectedRun?.WorkflowRunId != requestedRunId
                || requestVersion != nodeRunsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                NodeRuns.Clear();
                foreach (var nodeRun in response.Data)
                {
                    NodeRuns.Add(new NodeRunListItemViewModel(nodeRun, DisplayTextFormatter));
                }

                NodeRunMessage = F("format.loaded_node_runs", NodeRuns.Count);
                return;
            }

            NodeRunMessage = T("node_runs.refresh_failed");
            NodeRunErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == nodeRunsLoadVersion)
            {
                IsLoadingNodeRuns = false;
            }
        }
    }
}
