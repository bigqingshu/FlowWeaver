using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeEditorResolverTests
{
    [TestMethod]
    public void ResolveReturnsSchemaBackedJsonFallbackEditor()
    {
        var resolver = new NodeEditorResolver(BuiltinNodeEditors.CreateRegistry());
        resolver.ReplaceSchemaFallbackNodes(
            new[] { ("GenerateTestTableNode", "Generate Test Table") });

        var resolution = resolver.Resolve("GenerateTestTableNode");

        Assert.AreEqual("GenerateTestTableNode", resolution.NodeType);
        Assert.AreEqual("Generate Test Table", resolution.DisplayName);
        Assert.AreEqual(NodeEditorKind.JsonFallback, resolution.Kind);
        Assert.IsTrue(resolution.HasRegisteredEditor);
        Assert.IsTrue(resolution.UsesJsonFallback);
        Assert.AreEqual(
            NodeEditorResolution.JsonFallbackStatusKey,
            resolution.StatusKey);
        Assert.AreEqual(NodeEditorKey.None, resolution.EditorKey);
    }

    [TestMethod]
    public void ResolveDoesNotTreatStaticBuiltinFallbackListAsRequired()
    {
        var resolver = new NodeEditorResolver(BuiltinNodeEditors.CreateRegistry());

        var resolution = resolver.Resolve("GenerateTestTableNode", "Generate rows");

        Assert.AreEqual("GenerateTestTableNode", resolution.NodeType);
        Assert.AreEqual("Generate rows", resolution.DisplayName);
        Assert.AreEqual(NodeEditorKind.JsonFallback, resolution.Kind);
        Assert.IsFalse(resolution.HasRegisteredEditor);
        Assert.IsTrue(resolution.UsesJsonFallback);
        Assert.AreEqual(
            NodeEditorResolution.UnregisteredJsonFallbackStatusKey,
            resolution.StatusKey);
    }

    [TestMethod]
    public void ResolveReturnsUnregisteredJsonFallbackForUnknownNode()
    {
        var resolver = new NodeEditorResolver(BuiltinNodeEditors.CreateRegistry());

        var resolution = resolver.Resolve("CustomNode", "Custom Node");

        Assert.AreEqual("CustomNode", resolution.NodeType);
        Assert.AreEqual("Custom Node", resolution.DisplayName);
        Assert.AreEqual(NodeEditorKind.JsonFallback, resolution.Kind);
        Assert.IsFalse(resolution.HasRegisteredEditor);
        Assert.IsTrue(resolution.UsesJsonFallback);
        Assert.AreEqual(
            NodeEditorResolution.UnregisteredJsonFallbackStatusKey,
            resolution.StatusKey);
    }

    [TestMethod]
    public void ResolveUsesNodeTypeAsDisplayNameWhenUnknownDisplayNameIsMissing()
    {
        var resolver = new NodeEditorResolver(BuiltinNodeEditors.CreateRegistry());

        var resolution = resolver.Resolve("CustomNode");

        Assert.AreEqual("CustomNode", resolution.DisplayName);
    }

    [TestMethod]
    public void ResolveReturnsBuiltInEditorWhenDescriptorIsBuiltIn()
    {
        var registry = new NodeEditorRegistry();
        registry.Register(new NodeEditorDescriptor(
            "PublishSharedTablesNode",
            "Publish Shared Tables",
            NodeEditorKind.BuiltIn,
            NodeEditorKey.PublishSharedTables));
        var resolver = new NodeEditorResolver(registry);

        var resolution = resolver.Resolve("PublishSharedTablesNode");

        Assert.AreEqual("PublishSharedTablesNode", resolution.NodeType);
        Assert.AreEqual("Publish Shared Tables", resolution.DisplayName);
        Assert.AreEqual(NodeEditorKind.BuiltIn, resolution.Kind);
        Assert.IsTrue(resolution.HasRegisteredEditor);
        Assert.IsFalse(resolution.UsesJsonFallback);
        Assert.AreEqual(
            NodeEditorResolution.BuiltInStatusKey,
            resolution.StatusKey);
        Assert.AreEqual(NodeEditorKey.PublishSharedTables, resolution.EditorKey);
    }
}
