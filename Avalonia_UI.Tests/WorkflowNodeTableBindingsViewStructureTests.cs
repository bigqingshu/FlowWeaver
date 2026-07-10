using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowNodeTableBindingsViewStructureTests
{
    [TestMethod]
    public void SummaryPlacesTableBindingsAfterSelectedNodeConfiguration()
    {
        var summary = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");
        var configIndex = summary.IndexOf(
            "<workflow:WorkflowSelectedNodeConfigView />",
            StringComparison.Ordinal);
        var bindingsIndex = summary.IndexOf(
            "<workflow:WorkflowNodeTableBindingsView DataContext=\"{Binding WorkflowNodeTableBindings}\" />",
            StringComparison.Ordinal);

        Assert.IsGreaterThanOrEqualTo(0, configIndex);
        Assert.IsGreaterThan(configIndex, bindingsIndex);
    }

    [TestMethod]
    public void ComponentUsesSlotDrivenSelectorsAndSeparateCards()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeTableBindingsView.axaml");

        StringAssert.Contains(xaml, "IsVisible=\"{Binding HasSlots}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding InputBindings}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding Sources}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding OutputTargets}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding TargetKinds}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsNewTarget}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsExistingTarget}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding ApplyBindingsCommand}\"");
        Assert.AreEqual(2, CountOccurrences(xaml, "<Border Classes=\"Card\""));
    }

    private static int CountOccurrences(string value, string pattern)
    {
        var count = 0;
        var index = 0;
        while ((index = value.IndexOf(pattern, index, StringComparison.Ordinal)) >= 0)
        {
            count++;
            index += pattern.Length;
        }

        return count;
    }

    private static string ReadSourceFile(params string[] pathParts)
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI")) &&
                Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI.Tests")))
            {
                return File.ReadAllText(
                    Path.Combine(pathParts.Prepend(directory.FullName).ToArray()));
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate FlowWeaver repository root.");
    }
}
