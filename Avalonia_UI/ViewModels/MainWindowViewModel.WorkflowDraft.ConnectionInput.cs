using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ResetNewDraftConnectionInput()
    {
        lastSuggestedNewDraftConnectionId = string.Empty;
        SelectedNewDraftConnectionSourceNode = null;
        SelectedNewDraftConnectionTargetNode = null;
        NewDraftConnectionId = string.Empty;
        NewDraftConnectionSourceNodeId = string.Empty;
        NewDraftConnectionSourcePort = string.Empty;
        NewDraftConnectionTargetNodeId = string.Empty;
        NewDraftConnectionTargetPort = string.Empty;
    }

    private void ClearSelectedNewDraftConnectionNodesIfMissing()
    {
        if (SelectedNewDraftConnectionSourceNode is not null)
        {
            SelectedNewDraftConnectionSourceNode = FindDraftNode(
                SelectedNewDraftConnectionSourceNode.NodeInstanceId);
        }

        if (SelectedNewDraftConnectionTargetNode is not null)
        {
            SelectedNewDraftConnectionTargetNode = FindDraftNode(
                SelectedNewDraftConnectionTargetNode.NodeInstanceId);
        }
    }

    private void ApplySelectedNewDraftConnectionSourceNode(
        WorkflowDefinitionDraftNode node)
    {
        NewDraftConnectionSourceNodeId = node.NodeInstanceId;
        ApplySuggestedNewDraftConnectionId();
    }

    private void ApplySelectedNewDraftConnectionTargetNode(
        WorkflowDefinitionDraftNode node)
    {
        NewDraftConnectionTargetNodeId = node.NodeInstanceId;
        ApplySuggestedNewDraftConnectionId();
    }

    private void ApplySuggestedNewDraftConnectionId()
    {
        if (string.IsNullOrWhiteSpace(NewDraftConnectionSourceNodeId) ||
            string.IsNullOrWhiteSpace(NewDraftConnectionTargetNodeId) ||
            !ShouldApplySuggestedNewDraftConnectionId())
        {
            return;
        }

        lastSuggestedNewDraftConnectionId = BuildUniqueNewDraftConnectionId(
            NewDraftConnectionSourceNodeId,
            NewDraftConnectionTargetNodeId);
        NewDraftConnectionId = lastSuggestedNewDraftConnectionId;
    }

    private bool ShouldApplySuggestedNewDraftConnectionId()
    {
        return string.IsNullOrWhiteSpace(NewDraftConnectionId)
            || string.Equals(
                NewDraftConnectionId,
                lastSuggestedNewDraftConnectionId,
                StringComparison.Ordinal);
    }

    private string BuildUniqueNewDraftConnectionId(
        string sourceNodeId,
        string targetNodeId)
    {
        var baseId = BuildNewDraftConnectionIdBase(sourceNodeId, targetNodeId);
        var existingIds = WorkflowDefinitionDraftStructure?.Connections
            .Select(connection => connection.ConnectionId)
            .ToHashSet(StringComparer.Ordinal)
            ?? new HashSet<string>(StringComparer.Ordinal);

        var candidate = baseId;
        var suffix = 2;
        while (existingIds.Contains(candidate))
        {
            candidate = $"{baseId}_{suffix}";
            suffix++;
        }

        return candidate;
    }

    private static string BuildNewDraftConnectionIdBase(
        string sourceNodeId,
        string targetNodeId)
    {
        return
            $"{BuildSnakeCaseIdentifier(sourceNodeId, "source")}_to_{BuildSnakeCaseIdentifier(targetNodeId, "target")}";
    }

    partial void OnSelectedNewDraftConnectionSourceNodeChanged(
        WorkflowDefinitionDraftNode? value)
    {
        if (value is not null)
        {
            ApplySelectedNewDraftConnectionSourceNode(value);
        }
    }

    partial void OnSelectedNewDraftConnectionTargetNodeChanged(
        WorkflowDefinitionDraftNode? value)
    {
        if (value is not null)
        {
            ApplySelectedNewDraftConnectionTargetNode(value);
        }
    }
}
