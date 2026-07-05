using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record WorkflowDefinitionLinearChainAnalysis
{
    public bool IsLinear { get; init; }

    public string? Warning { get; init; }

    public IReadOnlyList<string> NodeInstanceIds { get; init; } = [];

    public static WorkflowDefinitionLinearChainAnalysis Linear(
        IReadOnlyList<string> nodeInstanceIds)
    {
        return new WorkflowDefinitionLinearChainAnalysis
        {
            IsLinear = true,
            NodeInstanceIds = nodeInstanceIds,
        };
    }

    public static WorkflowDefinitionLinearChainAnalysis Rejected(string warning)
    {
        return new WorkflowDefinitionLinearChainAnalysis
        {
            IsLinear = false,
            Warning = warning,
        };
    }
}
