using System.Linq;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class BuiltinNodeEditorsTests
{
    [TestMethod]
    public void AllContainsVisibleBuiltInNodesOnly()
    {
        CollectionAssert.AreEqual(
            new[]
            {
                "GenerateTestTableNode",
                "FilterRowsNode",
                "PublishSharedTablesNode",
                "ReadSharedTablesNode",
            },
            BuiltinNodeEditors.All.Select(editor => editor.NodeType).ToArray());

        Assert.IsFalse(BuiltinNodeEditors.All.Any(editor => editor.NodeType == "DelayTestNode"));
        Assert.IsFalse(BuiltinNodeEditors.All.Any(editor => editor.NodeType == "FaultTestNode"));
    }

    [TestMethod]
    public void AllUsesJsonFallbackUntilDedicatedEditorsExist()
    {
        foreach (var editor in BuiltinNodeEditors.All)
        {
            Assert.AreEqual(NodeEditorKind.JsonFallback, editor.Kind);
            Assert.IsNull(editor.ViewTypeName);
            Assert.IsTrue(editor.SupportsFallbackToJson);
        }
    }

    [TestMethod]
    public void CreateRegistryRegistersAllBuiltInEditors()
    {
        var registry = BuiltinNodeEditors.CreateRegistry();

        foreach (var editor in BuiltinNodeEditors.All)
        {
            Assert.AreEqual(editor, registry.Find(editor.NodeType));
        }

        Assert.IsNull(registry.Find("DelayTestNode"));
        Assert.IsNull(registry.Find("FaultTestNode"));
    }
}
