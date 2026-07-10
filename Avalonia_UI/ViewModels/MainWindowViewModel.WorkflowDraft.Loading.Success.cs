using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyWorkflowDefinitionLoadSuccess(
        WorkflowDefinitionDto workflow,
        IReadOnlyList<WorkflowRevisionDto> revisions)
    {
        WorkflowDefinitionDetail = new WorkflowDefinitionDetailViewModel(
            workflow,
            revisions,
            DisplayTextFormatter,
            _nodeEditorResolver);
        SelectedWorkflowDefinitionNode =
            WorkflowDefinitionDetail.Nodes.FirstOrDefault();
        workflowDefinitionDraftDocumentState.AcceptOriginalDefinition(
            WorkflowDefinitionDetail.RawDefinitionJson);
        WorkflowDefinitionDraftJson =
            workflowDefinitionDraftDocumentState.OriginalDefinitionJson;
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
}
