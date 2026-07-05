using System;
using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowSummaryViewHeadlessSmokeTests
{
    [TestMethod]
    public void WorkflowSummaryViewKeepsAddNodePanelBindingsInSourceXaml()
    {
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");
        var nodeListXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeListView.axaml");
        var addNodeXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowAddNodeView.axaml");

        StringAssert.Contains(
            summaryXaml,
            "Command=\"{Binding OpenWorkflowAddNodePanelCommand}\"");
        StringAssert.Contains(
            summaryXaml,
            "<workflow:WorkflowAddNodeView IsVisible=\"{Binding IsWorkflowAddNodePanelVisible}\"/>");
        Assert.IsFalse(
            nodeListXaml.Contains("OpenWorkflowAddNodePanelCommand", StringComparison.Ordinal),
            "The node management column should not host add-node controls.");
        Assert.IsFalse(
            nodeListXaml.Contains("<workflow:WorkflowAddNodeView", StringComparison.Ordinal),
            "The node management column should not host the add-node panel.");
        StringAssert.Contains(
            addNodeXaml,
            "ItemsSource=\"{Binding NodeDefinitions}\"");
        StringAssert.Contains(
            addNodeXaml,
            "SelectedItem=\"{Binding SelectedNewDraftNodeDefinition, Mode=TwoWay}\"");
        StringAssert.Contains(
            addNodeXaml,
            "Command=\"{Binding CloseWorkflowAddNodePanelCommand}\"");
        StringAssert.Contains(
            addNodeXaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftNodeCommand}\"");
        Assert.IsFalse(
            addNodeXaml.Contains("NewDraftNodeInstanceId", StringComparison.Ordinal),
            "The add-node panel should not expose node identity editing.");
        Assert.IsFalse(
            addNodeXaml.Contains("NewDraftNodeConfigJson", StringComparison.Ordinal),
            "The add-node panel should not expose config JSON editing.");
    }

    private static string ReadSourceFile(params string[] pathParts)
    {
        return File.ReadAllText(Path.Combine(FindRepoRoot(), Path.Combine(pathParts)));
    }

    private static string FindRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI"))
                && Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI.Tests")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not find the FlowWeaver repository root.");
    }
}
