using System;
using System.Collections.Generic;
using System.Linq;

namespace Avalonia_UI.Models;

public sealed class NodeEditorRegistry
{
    private readonly Dictionary<string, NodeEditorDescriptor> _descriptors = new(StringComparer.Ordinal);

    public IReadOnlyList<NodeEditorDescriptor> ListEditors()
    {
        return _descriptors
            .Values
            .OrderBy(descriptor => descriptor.NodeType, StringComparer.Ordinal)
            .ToArray();
    }

    public void Register(NodeEditorDescriptor descriptor)
    {
        ArgumentNullException.ThrowIfNull(descriptor);

        if (_descriptors.ContainsKey(descriptor.NodeType))
        {
            throw new InvalidOperationException($"Duplicate node editor registration: {descriptor.NodeType}");
        }

        _descriptors.Add(descriptor.NodeType, descriptor);
    }

    public NodeEditorDescriptor? Find(string nodeType)
    {
        if (string.IsNullOrWhiteSpace(nodeType))
        {
            return null;
        }

        return _descriptors.TryGetValue(nodeType, out var descriptor)
            ? descriptor
            : null;
    }
}
