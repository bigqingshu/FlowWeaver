using System;
using System.Collections.Generic;
using System.Linq;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool ShouldApplySuggestedNewDraftNodeInstanceId()
    {
        return string.IsNullOrWhiteSpace(NewDraftNodeInstanceId)
            || string.Equals(
                NewDraftNodeInstanceId,
                lastSuggestedNewDraftNodeInstanceId,
                StringComparison.Ordinal);
    }

    private bool ShouldApplySuggestedNewDraftNodeConfigJson()
    {
        return string.IsNullOrWhiteSpace(NewDraftNodeConfigJson)
            || string.Equals(NewDraftNodeConfigJson.Trim(), "{}", StringComparison.Ordinal)
            || string.Equals(
                NewDraftNodeConfigJson,
                lastSuggestedNewDraftNodeConfigJson,
                StringComparison.Ordinal);
    }

    private string BuildUniqueNewDraftNodeInstanceId(string nodeType)
    {
        var baseId = BuildNewDraftNodeInstanceIdBase(nodeType);
        var existingIds = WorkflowDefinitionDraftStructure?.Nodes
            .Select(node => node.NodeInstanceId)
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

    private static string BuildNewDraftNodeInstanceIdBase(string nodeType)
    {
        var source = string.IsNullOrWhiteSpace(nodeType)
            ? "node"
            : nodeType.Trim();

        if (source.EndsWith("Node", StringComparison.Ordinal) && source.Length > 4)
        {
            source = source[..^4];
        }

        return BuildSnakeCaseIdentifier(source, "node");
    }
}
