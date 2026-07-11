using System;

namespace Avalonia_UI.Models;

public sealed record NodeEditorDescriptor
{
    public NodeEditorDescriptor(
        string nodeType,
        string displayName,
        NodeEditorKind kind,
        NodeEditorKey editorKey = NodeEditorKey.None,
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

        if (kind == NodeEditorKind.BuiltIn && editorKey == NodeEditorKey.None)
        {
            throw new ArgumentException(
                "Built-in node editors must declare an editor key.",
                nameof(editorKey));
        }

        if (kind == NodeEditorKind.JsonFallback && editorKey != NodeEditorKey.None)
        {
            throw new ArgumentException(
                "JSON fallback editors cannot declare a built-in editor key.",
                nameof(editorKey));
        }

        NodeType = nodeType;
        DisplayName = displayName;
        Kind = kind;
        EditorKey = editorKey;
        SupportsFallbackToJson = supportsFallbackToJson;
    }

    public string NodeType { get; }

    public string DisplayName { get; }

    public NodeEditorKind Kind { get; }

    public NodeEditorKey EditorKey { get; }

    public bool SupportsFallbackToJson { get; }
}
