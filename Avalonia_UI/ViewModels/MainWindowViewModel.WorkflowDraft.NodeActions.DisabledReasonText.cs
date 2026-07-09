namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public string? CopyWorkflowDefinitionDraftNodeDisabledReasonText =>
        GetSelectedWorkflowDefinitionNodeMutationDisabledReason();

    public string? DeleteWorkflowDefinitionDraftNodeDisabledReasonText =>
        GetSelectedWorkflowDefinitionNodeMutationDisabledReason();

    public string? DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText =>
        GetSelectedWorkflowDefinitionDraftNodesMutationDisabledReason();

    public string? MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText =>
        GetMoveSelectedWorkflowDefinitionDraftNodeDisabledReason(offset: -1);

    public string? MoveSelectedWorkflowDefinitionDraftNodeDownDisabledReasonText =>
        GetMoveSelectedWorkflowDefinitionDraftNodeDisabledReason(offset: 1);
}
