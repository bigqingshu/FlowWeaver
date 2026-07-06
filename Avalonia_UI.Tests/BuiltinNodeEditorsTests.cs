using System.Linq;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class BuiltinNodeEditorsTests
{
    [TestMethod]
    public void AllIsEmptyUntilDedicatedEditorsExist()
    {
        Assert.IsEmpty(BuiltinNodeEditors.All);
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

        Assert.IsEmpty(registry.ListEditors());
    }
}
