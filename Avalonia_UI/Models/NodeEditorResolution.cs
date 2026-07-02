namespace Avalonia_UI.Models;

public sealed record NodeEditorResolution(
    string NodeType,
    NodeEditorKind Kind,
    string DisplayName,
    bool HasRegisteredEditor,
    bool UsesJsonFallback,
    string StatusText)
{
    public static NodeEditorResolution JsonFallback(
        string nodeType,
        string displayName,
        bool hasRegisteredEditor)
    {
        return new NodeEditorResolution(
            nodeType,
            NodeEditorKind.JsonFallback,
            displayName,
            hasRegisteredEditor,
            true,
            "JSON fallback");
    }

    public static NodeEditorResolution BuiltIn(NodeEditorDescriptor descriptor)
    {
        return new NodeEditorResolution(
            descriptor.NodeType,
            NodeEditorKind.BuiltIn,
            descriptor.DisplayName,
            true,
            false,
            "Built-in editor");
    }
}
