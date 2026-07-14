using System;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class RunLoopMonitorViewStructureTests
{
    [TestMethod]
    public void RunMonitorKeepsThreeColumnsAndHostsLoopMonitorInDetailTabs()
    {
        var pageXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Pages",
            "RunMonitorPage.axaml");
        var document = XDocument.Parse(pageXaml);
        var avalonia = document.Root!.Name.Namespace;
        var detailTabs = document
            .Descendants(avalonia + "TabControl")
            .Single(element => (string?)element.Attribute("Grid.Column") == "2");

        StringAssert.Contains(pageXaml, "ColumnDefinitions=\"340, 1.3*, 1*\"");
        Assert.AreEqual(
            "{Binding SelectedRunMonitorTabIndex, Mode=TwoWay}",
            (string?)detailTabs.Attribute("SelectedIndex"));
        StringAssert.Contains(pageXaml, "<rm:RunDetailPanelView />");
        StringAssert.Contains(
            pageXaml,
            "<rm:RunLoopMonitorView DataContext=\"{Binding RunLoopMonitor}\" />");
        Assert.IsFalse(pageXaml.Contains("Grid.Column=\"3\"", StringComparison.Ordinal));
    }

    [TestMethod]
    public void LoopMonitorViewLoadsSelectionsProgressively()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "RunMonitor",
            "RunLoopMonitorView.axaml");

        StringAssert.Contains(xaml, "x:DataType=\"vm:RunLoopMonitorViewModel\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding Loops}\"");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding SelectedLoop, Mode=TwoWay}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding Iterations}\"");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding SelectedIteration, Mode=TwoWay}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding IterationNodes}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding IterationTableRefs}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding LoadMoreLoopsCommand}\"");
        StringAssert.Contains(xaml, "Header=\"{Binding LoopDetailsText}\"");
        StringAssert.Contains(xaml, "Header=\"{Binding IterationDetailsText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SelectedLoop.ExitReasonText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SelectedIteration.InputTableRefIdText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SelectedIteration.OutputTableRefIdText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SelectedIteration.FailedNodeRunIdText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DiagnosticText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding ErrorJson}\"");
        Assert.IsFalse(xaml.Contains("IEngineHostApiClient", StringComparison.Ordinal));
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
