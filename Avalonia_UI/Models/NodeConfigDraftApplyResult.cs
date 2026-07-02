namespace Avalonia_UI.Models;

public sealed record NodeConfigDraftApplyResult
{
    public NodeConfigDraftApplyStatus Status { get; init; }

    public string UpdatedWorkflowDefinitionDraftJson { get; init; } = string.Empty;

    public string? Warning { get; init; }

    public bool Succeeded => Status == NodeConfigDraftApplyStatus.Succeeded;
}
