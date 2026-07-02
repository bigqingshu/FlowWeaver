using System;

namespace Avalonia_UI.Models;

public sealed class NodeEditorResolver
{
    private readonly NodeEditorRegistry _registry;

    public NodeEditorResolver(NodeEditorRegistry registry)
    {
        _registry = registry ?? throw new ArgumentNullException(nameof(registry));
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
        if (descriptor is null)
        {
            return NodeEditorResolution.JsonFallback(
                nodeType,
                displayName: string.IsNullOrWhiteSpace(displayName) ? nodeType : displayName,
                hasRegisteredEditor: false);
        }

        return descriptor.Kind == NodeEditorKind.BuiltIn
            ? NodeEditorResolution.BuiltIn(descriptor)
            : NodeEditorResolution.JsonFallback(
                descriptor.NodeType,
                descriptor.DisplayName,
                hasRegisteredEditor: true);
    }
}
