using System;
using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed class WorkflowNodeSelectionState
{
    private string? selectedNodeId;
    private bool hadSelection;

    public void Capture(string? nodeId, bool hasSelection)
    {
        selectedNodeId = nodeId;
        hadSelection = hasSelection;
    }

    public string? ResolveSelectedNodeId(IReadOnlyList<string> availableNodeIds)
    {
        if (selectedNodeId is not null)
        {
            foreach (var nodeId in availableNodeIds)
            {
                if (string.Equals(nodeId, selectedNodeId, StringComparison.Ordinal))
                {
                    return selectedNodeId;
                }
            }
        }

        return hadSelection || availableNodeIds.Count == 0
            ? null
            : availableNodeIds[0];
    }
}
