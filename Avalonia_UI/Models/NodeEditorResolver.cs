using System;
using System.Collections.Generic;
using System.Linq;

namespace Avalonia_UI.Models;

public sealed class NodeEditorResolver
{
    private readonly NodeEditorRegistry _registry;
    private readonly Dictionary<(string NodeType, string NodeVersion), string>
        _schemaFallbackDisplayNames = new();
    private readonly Dictionary<(string NodeType, string NodeVersion), UnavailableNodeDefinition>
        _unavailableNodes = new();

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

            _schemaFallbackDisplayNames[(nodeType, string.Empty)] =
                string.IsNullOrWhiteSpace(displayName) ? nodeType : displayName;
        }
    }

    public void ReplaceSchemaFallbackNodes(
        IEnumerable<(string NodeType, string NodeVersion, string DisplayName)> nodes)
    {
        ArgumentNullException.ThrowIfNull(nodes);

        _schemaFallbackDisplayNames.Clear();
        foreach (var (nodeType, nodeVersion, displayName) in nodes)
        {
            if (string.IsNullOrWhiteSpace(nodeType)
                || string.IsNullOrWhiteSpace(nodeVersion))
            {
                continue;
            }

            _schemaFallbackDisplayNames[(nodeType, nodeVersion)] =
                string.IsNullOrWhiteSpace(displayName) ? nodeType : displayName;
        }
    }

    public void ReplaceUnavailableNodes(
        IEnumerable<(string NodeType, string NodeVersion, string DisplayName, string Reason)> nodes)
    {
        ArgumentNullException.ThrowIfNull(nodes);

        _unavailableNodes.Clear();
        foreach (var (nodeType, nodeVersion, displayName, reason) in nodes)
        {
            if (string.IsNullOrWhiteSpace(nodeType)
                || string.IsNullOrWhiteSpace(nodeVersion))
            {
                continue;
            }

            var key = (nodeType, nodeVersion);
            if (_unavailableNodes.TryGetValue(key, out var existing))
            {
                _unavailableNodes[key] = existing with
                {
                    Reason = string.Join("; ", new[] { existing.Reason, reason }
                        .Where(value => !string.IsNullOrWhiteSpace(value))
                        .Distinct(StringComparer.Ordinal)),
                };
                continue;
            }

            _unavailableNodes[key] = new UnavailableNodeDefinition(
                string.IsNullOrWhiteSpace(displayName) ? nodeType : displayName,
                reason);
        }
    }

    public NodeEditorResolution Resolve(
        string nodeType,
        string? displayName = null,
        string? nodeVersion = null)
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

        if (TryGetSchemaFallbackDisplayName(
                nodeType,
                nodeVersion,
                out var schemaDisplayName))
        {
            return NodeEditorResolution.JsonFallback(
                nodeType,
                schemaDisplayName,
                hasRegisteredEditor: true);
        }

        if (!string.IsNullOrWhiteSpace(nodeVersion)
            && _unavailableNodes.TryGetValue((nodeType, nodeVersion), out var unavailable))
        {
            return NodeEditorResolution.UnavailableJsonFallback(
                nodeType,
                unavailable.DisplayName,
                unavailable.Reason);
        }

        return NodeEditorResolution.JsonFallback(
            nodeType,
            displayName: string.IsNullOrWhiteSpace(displayName) ? nodeType : displayName,
            hasRegisteredEditor: false);
    }

    private bool TryGetSchemaFallbackDisplayName(
        string nodeType,
        string? nodeVersion,
        out string displayName)
    {
        if (!string.IsNullOrWhiteSpace(nodeVersion))
        {
            if (_schemaFallbackDisplayNames.TryGetValue(
                    (nodeType, nodeVersion),
                    out displayName!))
            {
                return true;
            }

            if (_schemaFallbackDisplayNames.TryGetValue(
                    (nodeType, string.Empty),
                    out displayName!))
            {
                return true;
            }

            displayName = string.Empty;
            return false;
        }

        if (_schemaFallbackDisplayNames.TryGetValue(
                (nodeType, string.Empty),
                out displayName!))
        {
            return true;
        }

        var matching = _schemaFallbackDisplayNames.FirstOrDefault(
            pair => string.Equals(pair.Key.NodeType, nodeType, StringComparison.Ordinal));
        displayName = matching.Value;
        return !string.IsNullOrWhiteSpace(displayName);
    }

    private sealed record UnavailableNodeDefinition(string DisplayName, string Reason);
}
