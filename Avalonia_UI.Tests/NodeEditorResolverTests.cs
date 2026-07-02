using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeEditorResolverTests
{
    [TestMethod]
    public void ResolveReturnsRegisteredJsonFallbackEditor()
    {
        var resolver = new NodeEditorResolver(BuiltinNodeEditors.CreateRegistry());

        var resolution = resolver.Resolve("GenerateTestTableNode");

        Assert.AreEqual("GenerateTestTableNode", resolution.NodeType);
        Assert.AreEqual("Generate Test Table", resolution.DisplayName);
        Assert.AreEqual(NodeEditorKind.JsonFallback, resolution.Kind);
        Assert.IsTrue(resolution.HasRegisteredEditor);
        Assert.IsTrue(resolution.UsesJsonFallback);
        Assert.AreEqual(
            NodeEditorResolution.JsonFallbackStatusKey,
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
            "SpecialNode",
            "Special Node",
            NodeEditorKind.BuiltIn,
            viewTypeName: "Avalonia_UI.Views.Components.Workflow.SpecialNodeEditorView"));
        var resolver = new NodeEditorResolver(registry);

        var resolution = resolver.Resolve("SpecialNode");

        Assert.AreEqual("SpecialNode", resolution.NodeType);
        Assert.AreEqual("Special Node", resolution.DisplayName);
        Assert.AreEqual(NodeEditorKind.BuiltIn, resolution.Kind);
        Assert.IsTrue(resolution.HasRegisteredEditor);
        Assert.IsFalse(resolution.UsesJsonFallback);
        Assert.AreEqual(
            NodeEditorResolution.BuiltInStatusKey,
            resolution.StatusKey);
    }
}
