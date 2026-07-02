using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record WorkflowDefinitionDraftStructure
{
    public WorkflowDefinitionDraftStructureStatus Status { get; init; } =
        WorkflowDefinitionDraftStructureStatus.JsonInvalid;

    public IReadOnlyList<WorkflowDefinitionDraftNode> Nodes { get; init; } = [];

    public IReadOnlyList<WorkflowDefinitionDraftConnection> Connections { get; init; } = [];

    public IReadOnlyList<string> Warnings { get; init; } = [];

    public bool IsSupported => Status == WorkflowDefinitionDraftStructureStatus.Supported;

    public int NodeCount => Nodes.Count;

    public int ConnectionCount => Connections.Count;
}
