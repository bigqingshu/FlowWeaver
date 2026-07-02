using System;

namespace Avalonia_UI.Models;

public sealed record NodeEditorDescriptor
{
    public NodeEditorDescriptor(
        string nodeType,
        string displayName,
        NodeEditorKind kind,
        string? viewTypeName = null,
        bool supportsFallbackToJson = true)
    {
        if (string.IsNullOrWhiteSpace(nodeType))
        {
            throw new ArgumentException("Node type must not be empty.", nameof(nodeType));
        }

        if (string.IsNullOrWhiteSpace(displayName))
        {
            throw new ArgumentException("Display name must not be empty.", nameof(displayName));
        }

        if (kind == NodeEditorKind.BuiltIn && string.IsNullOrWhiteSpace(viewTypeName))
        {
            throw new ArgumentException("Built-in node editors must declare a view type.", nameof(viewTypeName));
        }

        NodeType = nodeType;
        DisplayName = displayName;
        Kind = kind;
        ViewTypeName = viewTypeName;
        SupportsFallbackToJson = supportsFallbackToJson;
    }

    public string NodeType { get; }

    public string DisplayName { get; }

    public NodeEditorKind Kind { get; }

    public string? ViewTypeName { get; }

    public bool SupportsFallbackToJson { get; }
}
