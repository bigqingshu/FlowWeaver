namespace Avalonia_UI.Models;

public sealed record WorkflowDefinitionDraftRuntimeOptionsPatchResult
{
    public WorkflowDefinitionDraftRuntimeOptionsPatchStatus Status { get; init; }

    public string UpdatedWorkflowDefinitionDraftJson { get; init; } = string.Empty;

    public string? Warning { get; init; }

    public bool Succeeded =>
        Status == WorkflowDefinitionDraftRuntimeOptionsPatchStatus.Succeeded;
}
