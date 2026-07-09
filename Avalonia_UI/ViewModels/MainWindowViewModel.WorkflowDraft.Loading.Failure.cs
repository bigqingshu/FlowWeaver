using System.Collections.Generic;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyWorkflowDefinitionLoadFailure(
        ApiResponseEnvelope<WorkflowDefinitionDto> response)
    {
        WorkflowDefinitionDetail = null;
        SelectedWorkflowDefinitionNode = null;
        WorkflowDefinitionMessage = T("definition.load_failed");
        WorkflowDefinitionErrorMessage = DescribeError(response);
    }

    private void ApplyWorkflowDefinitionRevisionsLoadFailure(
        ApiResponseEnvelope<List<WorkflowRevisionDto>> response)
    {
        WorkflowDefinitionDetail = null;
        SelectedWorkflowDefinitionNode = null;
        WorkflowDefinitionMessage = T("definition.revisions_load_failed");
        WorkflowDefinitionErrorMessage = DescribeError(response);
    }
}
