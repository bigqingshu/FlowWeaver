using System.Linq;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshWorkflows()
    {
        return CanUseEngineActions && !IsWorkflowBusy;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshWorkflows))]
    private async Task RefreshWorkflowsAsync()
    {
        IsLoadingWorkflows = true;
        WorkflowMessage = T("workflow.loading");
        WorkflowErrorMessage = null;

        var response = await _apiClient.ListWorkflowsAsync(
            BuildSettings(),
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            var previousWorkflowId = SelectedWorkflow?.WorkflowId;
            Workflows.Clear();
            foreach (var workflow in response.Data)
            {
                Workflows.Add(new WorkflowListItemViewModel(workflow));
            }

            SelectedWorkflow = Workflows.FirstOrDefault(
                workflow => workflow.WorkflowId == previousWorkflowId)
                ?? Workflows.FirstOrDefault();
            WorkflowMessage = F("format.loaded_workflows", Workflows.Count);
            IsLoadingWorkflows = false;
            return;
        }

        WorkflowMessage = T("workflow.refresh_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsLoadingWorkflows = false;
    }

    private async Task RefreshWorkflowsAfterHealthyConnectionAsync()
    {
        if (Workflows.Count > 0 || !CanRefreshWorkflows())
        {
            return;
        }

        await RefreshWorkflowsAsync();
        if (CanLoadSelectedWorkflowDefinition())
        {
            await LoadSelectedWorkflowDefinitionAsync();
        }
    }

    private async Task RefreshWorkflowsSelectingAsync(string workflowId)
    {
        IsLoadingWorkflows = true;
        WorkflowMessage = T("workflow.refreshing");
        WorkflowErrorMessage = null;

        var response = await _apiClient.ListWorkflowsAsync(
            BuildSettings(),
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            Workflows.Clear();
            foreach (var workflow in response.Data)
            {
                Workflows.Add(new WorkflowListItemViewModel(workflow));
            }

            SelectedWorkflow = Workflows.FirstOrDefault(workflow => workflow.WorkflowId == workflowId)
                ?? Workflows.FirstOrDefault();
            WorkflowMessage = F("format.loaded_workflows", Workflows.Count);
            IsLoadingWorkflows = false;
            return;
        }

        WorkflowMessage = T("workflow.refresh_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsLoadingWorkflows = false;
    }
}
