using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowNodeCatalogViewStructureTests
{
    [TestMethod]
    public void CatalogViewUsesReadOnlyNodeDefinitionsBinding()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeCatalogView.axaml");

        StringAssert.Contains(xaml, "Command=\"{Binding RefreshNodeDefinitionsCommand}\"");
        StringAssert.Contains(xaml, "ToolTip.Tip=\"{Binding RefreshNodeDefinitionsDisabledReasonText}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding NodeDefinitions}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding HasNodeDefinitions}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding HasNodeDefinitionCatalogEmptyState}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeCatalogEmptyStateText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DisplayNameText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding InputPortsText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding OutputPortsText}\"");
    }

    [TestMethod]
    public void CatalogViewDoesNotIntroduceNodeMutationActions()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeCatalogView.axaml");

        Assert.IsFalse(xaml.Contains("CreateNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("AddNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("EditNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ConfigureNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("SaveNode", StringComparison.Ordinal));
    }

    private static string ReadSourceFile(params string[] pathParts)
    {
        var repoRoot = GetRepoRoot();
        return File.ReadAllText(Path.Combine(pathParts.Prepend(repoRoot).ToArray()));
    }

    private static string GetRepoRoot()
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

        throw new DirectoryNotFoundException("Could not locate FlowWeaver repository root.");
    }
}
