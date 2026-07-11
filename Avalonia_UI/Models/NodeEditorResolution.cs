namespace Avalonia_UI.Models;

public sealed record NodeEditorResolution(
    string NodeType,
    NodeEditorKind Kind,
    string DisplayName,
    bool HasRegisteredEditor,
    bool UsesJsonFallback,
    string StatusKey,
    NodeEditorKey EditorKey)
{
    public const string BuiltInStatusKey = "node_editor.status.builtin";

    public const string JsonFallbackStatusKey = "node_editor.status.json_fallback";

    public const string UnregisteredJsonFallbackStatusKey =
        "node_editor.status.unregistered_json_fallback";

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
            hasRegisteredEditor
                ? JsonFallbackStatusKey
                : UnregisteredJsonFallbackStatusKey,
            NodeEditorKey.None);
    }

    public static NodeEditorResolution BuiltIn(NodeEditorDescriptor descriptor)
    {
        return new NodeEditorResolution(
            descriptor.NodeType,
            NodeEditorKind.BuiltIn,
            descriptor.DisplayName,
            true,
            false,
            BuiltInStatusKey,
            descriptor.EditorKey);
    }
}
