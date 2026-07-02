using System;
using System.Linq;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeEditorRegistryTests
{
    [TestMethod]
    public void DescriptorAllowsJsonFallbackWithoutViewType()
    {
        var descriptor = new NodeEditorDescriptor(
            "GenerateTestTableNode",
            "Generate Test Table",
            NodeEditorKind.JsonFallback);

        Assert.AreEqual("GenerateTestTableNode", descriptor.NodeType);
        Assert.AreEqual("Generate Test Table", descriptor.DisplayName);
        Assert.AreEqual(NodeEditorKind.JsonFallback, descriptor.Kind);
        Assert.IsNull(descriptor.ViewTypeName);
        Assert.IsTrue(descriptor.SupportsFallbackToJson);
    }

    [TestMethod]
    public void DescriptorRequiresBuiltInViewType()
    {
        var exception = Assert.ThrowsExactly<ArgumentException>(
            () => new NodeEditorDescriptor(
                "FilterRowsNode",
                "Filter Rows",
                NodeEditorKind.BuiltIn));

        Assert.AreEqual("viewTypeName", exception.ParamName);
    }

    [TestMethod]
    public void RegistryRegistersAndFindsEditorsByNodeType()
    {
        var registry = new NodeEditorRegistry();
        var descriptor = new NodeEditorDescriptor(
            "FilterRowsNode",
            "Filter Rows",
            NodeEditorKind.JsonFallback);

        registry.Register(descriptor);

        Assert.AreSame(descriptor, registry.Find("FilterRowsNode"));
        Assert.IsNull(registry.Find("MissingNode"));
        Assert.IsNull(registry.Find(string.Empty));
    }

    [TestMethod]
    public void RegistryRejectsDuplicateNodeTypes()
    {
        var registry = new NodeEditorRegistry();
        registry.Register(new NodeEditorDescriptor(
            "ReadSharedTablesNode",
            "Read Shared Tables",
            NodeEditorKind.JsonFallback));

        var exception = Assert.ThrowsExactly<InvalidOperationException>(
            () => registry.Register(new NodeEditorDescriptor(
                "ReadSharedTablesNode",
                "Read Shared Tables Again",
                NodeEditorKind.JsonFallback)));

        StringAssert.Contains(exception.Message, "ReadSharedTablesNode");
    }

    [TestMethod]
    public void RegistryListsEditorsInStableNodeTypeOrder()
    {
        var registry = new NodeEditorRegistry();
        registry.Register(new NodeEditorDescriptor(
            "PublishSharedTablesNode",
            "Publish Shared Tables",
            NodeEditorKind.JsonFallback));
        registry.Register(new NodeEditorDescriptor(
            "GenerateTestTableNode",
            "Generate Test Table",
            NodeEditorKind.JsonFallback));

        CollectionAssert.AreEqual(
            new[] { "GenerateTestTableNode", "PublishSharedTablesNode" },
            registry.ListEditors().Select(descriptor => descriptor.NodeType).ToArray());
    }
}
