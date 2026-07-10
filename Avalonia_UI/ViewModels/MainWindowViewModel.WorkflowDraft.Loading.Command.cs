using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanLoadSelectedWorkflowDefinition))]
    private async Task LoadSelectedWorkflowDefinitionAsync()
    {
        if (SelectedWorkflow is null)
        {
            return;
        }

        var workflowId = SelectedWorkflow.WorkflowId;
        var requestVersion = BeginWorkflowDefinitionLoad(SelectedWorkflow.Name);

        try
        {
            var workflowResponse = await _apiClient.GetWorkflowAsync(
                BuildSettings(),
                workflowId,
                _shutdown.Token);

            if (IsStaleWorkflowDefinitionLoadRequest(requestVersion, workflowId))
            {
                return;
            }

            if (!workflowResponse.Ok || workflowResponse.Data is null)
            {
                ApplyWorkflowDefinitionLoadFailure(workflowResponse);
                return;
            }

            var revisionsResponse = await _apiClient.ListWorkflowRevisionsAsync(
                BuildSettings(),
                workflowId,
                _shutdown.Token);

            if (IsStaleWorkflowDefinitionLoadRequest(requestVersion, workflowId))
            {
                return;
            }

            if (!revisionsResponse.Ok || revisionsResponse.Data is null)
            {
                ApplyWorkflowDefinitionRevisionsLoadFailure(revisionsResponse);
                return;
            }

            ApplyWorkflowDefinitionLoadSuccess(
                workflowResponse.Data,
                revisionsResponse.Data);
        }
        finally
        {
            CompleteWorkflowDefinitionLoad(requestVersion);
        }
    }
}
