using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowLoopRegionsViewStructureTests
{
    [TestMethod]
    public void WorkflowSummaryHostsIndependentLoopRegionsComponentAfterConnections()
    {
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        var connectionsIndex = summaryXaml.IndexOf(
            "Text=\"{Binding ConnectionsSectionText}\"",
            StringComparison.Ordinal);
        var loopRegionsIndex = summaryXaml.IndexOf(
            "<workflow:WorkflowLoopRegionsView DataContext=\"{Binding WorkflowLoopRegions}\" />",
            StringComparison.Ordinal);

        Assert.IsGreaterThanOrEqualTo(0, connectionsIndex);
        Assert.IsGreaterThan(connectionsIndex, loopRegionsIndex);
        Assert.IsFalse(summaryXaml.Contains("ItemsSource=\"{Binding Regions}\"", StringComparison.Ordinal));
    }

    [TestMethod]
    public void LoopRegionsComponentUsesStructuredDraftControlsAndConfirmation()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowLoopRegionsView.axaml");
        var codeBehind = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowLoopRegionsView.axaml.cs");

        StringAssert.Contains(xaml, "x:DataType=\"vm:WorkflowLoopRegionsViewModel\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding Regions}\"");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding SelectedRegion, Mode=TwoWay}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding NodeOptions}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding BodyNodeOptions}\"");
        StringAssert.Contains(xaml, "IsChecked=\"{Binding IsBodySelected, Mode=TwoWay}\"");
        StringAssert.Contains(xaml, "IsChecked=\"{Binding IsEnabledDraft, Mode=TwoWay}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding ApplyDraftCommand}\"");
        StringAssert.Contains(xaml, "Click=\"ConfirmDeleteLoopRegion\"");
        Assert.IsFalse(xaml.Contains("WorkflowDefinitionDraftJson", StringComparison.Ordinal));
        StringAssert.Contains(
            codeBehind,
            "await viewModel.DeleteSelectedRegionCommand.ExecuteAsync(null);");
    }

    [TestMethod]
    public void AdvancedJsonEditorBindsToDebouncedInputBuffer()
    {
        var editorXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowEditorView.axaml");

        StringAssert.Contains(
            editorXaml,
            "Text=\"{Binding AdvancedWorkflowDefinitionDraftJson, Mode=TwoWay}\"");
        Assert.IsFalse(
            editorXaml.Contains(
                "Text=\"{Binding WorkflowDefinitionDraftJson}\"",
                StringComparison.Ordinal));
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
            if (Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Repository root was not found.");
    }
}
