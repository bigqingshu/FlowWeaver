using System.Collections.Generic;

namespace Avalonia_UI.Models;

public static class BuiltinNodeEditors
{
    public static IReadOnlyList<NodeEditorDescriptor> All { get; } =
        new[]
        {
            JsonFallback("GenerateTestTableNode", "Generate Test Table"),
            JsonFallback("FilterRowsNode", "Filter Rows"),
            JsonFallback("PublishSharedTablesNode", "Publish Shared Tables"),
            JsonFallback("ReadSharedTablesNode", "Read Shared Tables"),
        };

    public static NodeEditorRegistry CreateRegistry()
    {
        var registry = new NodeEditorRegistry();
        foreach (var descriptor in All)
        {
            registry.Register(descriptor);
        }

        return registry;
    }

    private static NodeEditorDescriptor JsonFallback(string nodeType, string displayName)
    {
        return new NodeEditorDescriptor(
            nodeType,
            displayName,
            NodeEditorKind.JsonFallback);
    }
}
