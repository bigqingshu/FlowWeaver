namespace Avalonia_UI.Models;

public sealed record WorkflowDefinitionDraftNode
{
    public string NodeInstanceId { get; init; } = string.Empty;

    public string NodeType { get; init; } = string.Empty;

    public string NodeTypeDisplayName { get; init; } = string.Empty;

    public string NodeVersion { get; init; } = string.Empty;

    public string DisplayName { get; init; } = string.Empty;

    public bool Enabled { get; init; } = true;

    public string ConfigJson { get; init; } = "{}";

    public bool HasConfig { get; init; }
}
