using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record WorkflowDefinitionDraftNodePatchResult
{
    public WorkflowDefinitionDraftNodePatchStatus Status { get; init; }

    public string UpdatedWorkflowDefinitionDraftJson { get; init; } = string.Empty;

    public string? Warning { get; init; }

    public IReadOnlyList<WorkflowDefinitionDraftConnection> RemovedConnections { get; init; } =
        [];

    public bool Succeeded => Status == WorkflowDefinitionDraftNodePatchStatus.Succeeded;
}
