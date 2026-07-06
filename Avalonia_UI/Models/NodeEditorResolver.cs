using System;
using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed class NodeEditorResolver
{
    private readonly NodeEditorRegistry _registry;
    private readonly Dictionary<string, string> _schemaFallbackDisplayNames = new(StringComparer.Ordinal);

    public NodeEditorResolver(NodeEditorRegistry registry)
    {
        _registry = registry ?? throw new ArgumentNullException(nameof(registry));
    }

    public void ReplaceSchemaFallbackNodes(
        IEnumerable<(string NodeType, string DisplayName)> nodes)
    {
        ArgumentNullException.ThrowIfNull(nodes);

        _schemaFallbackDisplayNames.Clear();
        foreach (var (nodeType, displayName) in nodes)
        {
            if (string.IsNullOrWhiteSpace(nodeType))
            {
                continue;
            }

            _schemaFallbackDisplayNames[nodeType] =
                string.IsNullOrWhiteSpace(displayName) ? nodeType : displayName;
        }
    }

    public NodeEditorResolution Resolve(string nodeType, string? displayName = null)
    {
        if (string.IsNullOrWhiteSpace(nodeType))
        {
            return NodeEditorResolution.JsonFallback(
                string.Empty,
                displayName: displayName ?? string.Empty,
                hasRegisteredEditor: false);
        }

        var descriptor = _registry.Find(nodeType);
        if (descriptor?.Kind == NodeEditorKind.BuiltIn)
        {
            return NodeEditorResolution.BuiltIn(descriptor);
        }

        if (descriptor?.Kind == NodeEditorKind.JsonFallback)
        {
            return NodeEditorResolution.JsonFallback(
                descriptor.NodeType,
                descriptor.DisplayName,
                hasRegisteredEditor: true);
        }

        if (_schemaFallbackDisplayNames.TryGetValue(nodeType, out var schemaDisplayName))
        {
            return NodeEditorResolution.JsonFallback(
                nodeType,
                schemaDisplayName,
                hasRegisteredEditor: true);
        }

        return NodeEditorResolution.JsonFallback(
            nodeType,
            displayName: string.IsNullOrWhiteSpace(displayName) ? nodeType : displayName,
            hasRegisteredEditor: false);
    }
}
