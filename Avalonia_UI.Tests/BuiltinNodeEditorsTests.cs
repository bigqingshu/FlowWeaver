using System.Linq;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class BuiltinNodeEditorsTests
{
    [TestMethod]
    public void AllRegistersDedicatedEditors()
    {
        CollectionAssert.AreEqual(
            new[]
            {
                "SqlMappingNode",
                "PublishSharedTablesNode",
                "ReadSharedTablesNode",
            },
            BuiltinNodeEditors.All.Select(editor => editor.NodeType).ToArray());
        CollectionAssert.AreEqual(
            new[]
            {
                NodeEditorKey.SqlMappingTable,
                NodeEditorKey.PublishSharedTables,
                NodeEditorKey.ReadSharedTables,
            },
            BuiltinNodeEditors.All.Select(editor => editor.EditorKey).ToArray());
    }

    [TestMethod]
    public void AllDoesNotRegisterJsonFallbackEditors()
    {
        Assert.IsFalse(BuiltinNodeEditors.All.Any(editor =>
            editor.Kind == NodeEditorKind.JsonFallback));
    }

    [TestMethod]
    public void CreateRegistryRegistersAllBuiltInEditors()
    {
        var registry = BuiltinNodeEditors.CreateRegistry();

        foreach (var editor in BuiltinNodeEditors.All)
        {
            Assert.AreEqual(editor, registry.Find(editor.NodeType));
        }

        Assert.HasCount(3, registry.ListEditors());
    }
}
