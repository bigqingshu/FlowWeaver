using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
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
        var requestVersion = ++workflowDefinitionLoadVersion;
        IsLoadingWorkflowDefinition = true;
        WorkflowDefinitionMessage = F(
            "format.loading_definition_for",
            SelectedWorkflow.Name);
        WorkflowDefinitionErrorMessage = null;

        try
        {
            var workflowResponse = await _apiClient.GetWorkflowAsync(
                BuildSettings(),
                workflowId,
                _shutdown.Token);

            if (SelectedWorkflow?.WorkflowId != workflowId || requestVersion != workflowDefinitionLoadVersion)
            {
                return;
            }

            if (!workflowResponse.Ok || workflowResponse.Data is null)
            {
                WorkflowDefinitionDetail = null;
                SelectedWorkflowDefinitionNode = null;
                WorkflowDefinitionMessage = T("definition.load_failed");
                WorkflowDefinitionErrorMessage = DescribeError(workflowResponse);
                return;
            }

            var revisionsResponse = await _apiClient.ListWorkflowRevisionsAsync(
                BuildSettings(),
                workflowId,
                _shutdown.Token);

            if (SelectedWorkflow?.WorkflowId != workflowId || requestVersion != workflowDefinitionLoadVersion)
            {
                return;
            }

            if (!revisionsResponse.Ok || revisionsResponse.Data is null)
            {
                WorkflowDefinitionDetail = null;
                SelectedWorkflowDefinitionNode = null;
                WorkflowDefinitionMessage = T("definition.revisions_load_failed");
                WorkflowDefinitionErrorMessage = DescribeError(revisionsResponse);
                return;
            }

            WorkflowDefinitionDetail = new WorkflowDefinitionDetailViewModel(
                workflowResponse.Data,
                revisionsResponse.Data,
                DisplayTextFormatter,
                _nodeEditorResolver);
            SelectedWorkflowDefinitionNode =
                WorkflowDefinitionDetail.Nodes.FirstOrDefault();
            originalWorkflowDefinitionJson = WorkflowDefinitionDetail.RawDefinitionJson;
            WorkflowDefinitionDraftJson = originalWorkflowDefinitionJson;
            IsWorkflowDefinitionDraftDirty = false;
            HasWorkflowDefinitionRevisionConflict = false;
            WorkflowDefinitionValidationMessage = T("definition.draft_loaded");
            WorkflowDefinitionValidationErrorMessage = null;
            WorkflowDefinitionMessage =
                F(
                    "format.loaded_workflow_definition",
                    WorkflowDefinitionDetail.Name,
                    WorkflowDefinitionDetail.VersionText);
        }
        finally
        {
            if (requestVersion == workflowDefinitionLoadVersion)
            {
                IsLoadingWorkflowDefinition = false;
            }
        }
    }
}
