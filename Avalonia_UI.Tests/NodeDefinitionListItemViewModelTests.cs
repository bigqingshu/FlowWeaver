using Avalonia_UI.Api;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeDefinitionListItemViewModelTests
{
    [TestMethod]
    public void FormatsPortsAndStableSummaryText()
    {
        var item = new NodeDefinitionListItemViewModel(new NodeDefinitionDto
        {
            NodeType = "FilterRowsNode",
            NodeVersion = "1.0",
            DisplayName = "Filter Rows",
            InputPorts =
            [
                new NodePortDefinitionDto { Name = "in", Required = true },
                new NodePortDefinitionDto { Name = "side", Required = false },
            ],
            OutputPorts =
            [
                new NodePortDefinitionDto { Name = "out", Required = false },
            ],
            ExecutionMode = "PROCESS_POOL",
            DefaultTimeoutSeconds = 60,
            RetrySafe = false,
            UiVisibility = "visible",
        });

        Assert.AreEqual("Filter Rows", item.DisplayNameText);
        Assert.AreEqual("FilterRowsNode@1.0", item.TypeText);
        Assert.AreEqual("in*, side", item.InputPortsText);
        Assert.AreEqual("out", item.OutputPortsText);
        Assert.AreEqual("60s", item.TimeoutText);
    }

    [TestMethod]
    public void FallsBackForMissingOptionalDisplayValues()
    {
        var item = new NodeDefinitionListItemViewModel(new NodeDefinitionDto
        {
            NodeType = "GenerateTestTableNode",
            NodeVersion = "1.0",
            DisplayName = "",
            InputPorts = [],
            OutputPorts = [],
        });

        Assert.AreEqual("GenerateTestTableNode", item.DisplayNameText);
        Assert.AreEqual("-", item.InputPortsText);
        Assert.AreEqual("-", item.OutputPortsText);
    }
}
