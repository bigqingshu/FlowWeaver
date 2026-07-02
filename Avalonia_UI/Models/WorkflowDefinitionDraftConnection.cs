namespace Avalonia_UI.Models;

public sealed record WorkflowDefinitionDraftConnection
{
    public string ConnectionId { get; init; } = string.Empty;

    public string SourceNodeId { get; init; } = string.Empty;

    public string SourcePort { get; init; } = string.Empty;

    public string TargetNodeId { get; init; } = string.Empty;

    public string TargetPort { get; init; } = string.Empty;
}
