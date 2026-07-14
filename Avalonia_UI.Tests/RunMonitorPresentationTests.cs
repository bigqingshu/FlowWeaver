using System;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class RunMonitorPresentationTests
{
    [TestMethod]
    public void RunManagementFooterUsesWidthSafeRows()
    {
        var document = XDocument.Load(GetViewPath("RunListView.axaml"));
        var avalonia = document.Root!.Name.Namespace;
        var footer = document
            .Descendants(avalonia + "StackPanel")
            .Single(element => (string?)element.Attribute("Grid.Row") == "3");

        var pageText = footer
            .Elements(avalonia + "TextBlock")
            .Single(element =>
                (string?)element.Attribute("Text")
                == "{Binding BackgroundRunManagement.PageText}");
        Assert.AreEqual("Center", (string?)pageText.Attribute("HorizontalAlignment"));

        var grids = footer.Elements(avalonia + "Grid").ToArray();
        Assert.HasCount(2, grids);
        Assert.AreEqual("*,*", (string?)grids[0].Attribute("ColumnDefinitions"));
        Assert.AreEqual("*,*", (string?)grids[1].Attribute("ColumnDefinitions"));
        Assert.AreEqual(
            "Auto,Auto,Auto",
            (string?)grids[1].Attribute("RowDefinitions"));
        Assert.AreEqual("8", (string?)grids[1].Attribute("RowSpacing"));

        var pageButtons = grids[0].Elements(avalonia + "Button").ToArray();
        Assert.HasCount(2, pageButtons);
        Assert.IsTrue(pageButtons.All(IsWidthSafeButton));
        CollectionAssert.AreEqual(
            new[]
            {
                "{Binding BackgroundRunManagement.PreviousPageCommand}",
                "{Binding BackgroundRunManagement.NextPageCommand}",
            },
            pageButtons
                .Select(button => (string?)button.Attribute("Command"))
                .ToArray());

        var actionButtons = grids[1]
            .Elements()
            .SelectMany(element =>
                element.Name == avalonia + "Button"
                    ? new[] { element }
                    : element.Elements(avalonia + "Button"))
            .ToArray();
        Assert.HasCount(4, actionButtons);
        Assert.IsTrue(actionButtons.All(IsWidthSafeButton));
        Assert.IsTrue(document
            .Descendants(avalonia + "Button")
            .Any(button =>
                (string?)button.Attribute("Command")
                == "{Binding BackgroundRunManagement.DeleteRunCommand}"));

        var cancelCleanup = footer
            .Elements(avalonia + "Button")
            .Single(button =>
                (string?)button.Attribute("Command")
                == "{Binding BackgroundRunManagement.CancelCleanupTablesCommand}");
        Assert.IsTrue(IsWidthSafeButton(cancelCleanup));

        Assert.IsFalse(document
            .Descendants(avalonia + "Button")
            .Any(button =>
                (string?)button.Attribute("Command")
                == "{Binding BackgroundRunManagement.StartCommand}"));
        Assert.IsTrue(document
            .Descendants()
            .Any(element => element.Name.LocalName == "BackgroundRunLauncherView"));
    }

    [TestMethod]
    public void BackgroundRunLauncherUsesSharedModeTargetAndStartState()
    {
        var xaml = File.ReadAllText(GetViewPath("BackgroundRunLauncherView.axaml"));

        StringAssert.Contains(xaml, "Command=\"{Binding UseFullStartModeCommand}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding UsePreviewToNodeStartModeCommand}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding StartTargetNodes}\"");
        StringAssert.Contains(
            xaml,
            "SelectedItem=\"{Binding SelectedStartTargetNode, Mode=TwoWay}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding StartCommand}\"");
        StringAssert.Contains(xaml, "IsEnabled=\"{Binding CanStartBackgroundRun}\"");
    }

    [TestMethod]
    public void RunMonitorViewsBindLocalizedStatusText()
    {
        foreach (var fileName in new[]
        {
            "RunListView.axaml",
            "NodeRunListView.axaml",
            "RunLoopMonitorView.axaml",
        })
        {
            var document = XDocument.Load(GetViewPath(fileName));
            var avalonia = document.Root!.Name.Namespace;
            Assert.IsTrue(document
                .Descendants(avalonia + "TextBlock")
                .Any(element =>
                    (string?)element.Attribute("Text") == "{Binding StatusText}"));
        }
    }

    [TestMethod]
    public void RunOverviewUsesLazyTabStateAndDedicatedViewModel()
    {
        var pageXaml = File.ReadAllText(GetPagePath("RunMonitorPage.axaml"));
        StringAssert.Contains(
            pageXaml,
            "SelectedIndex=\"{Binding SelectedRunMonitorTabIndex, Mode=TwoWay}\"");

        var detailXaml = File.ReadAllText(GetViewPath("RunDetailPanelView.axaml"));
        StringAssert.Contains(
            detailXaml,
            "<rm:RunOverviewView Grid.Row=\"5\" DataContext=\"{Binding RunOverview}\"/>");
    }

    [TestMethod]
    public void NodeRunMonitorUsesPagedSelectionAndDetails()
    {
        var pageXaml = File.ReadAllText(GetPagePath("RunMonitorPage.axaml"));
        StringAssert.Contains(
            pageXaml,
            "<rm:NodeRunListView Grid.Column=\"1\" DataContext=\"{Binding NodeRunMonitor}\" />");

        var nodeXaml = File.ReadAllText(GetViewPath("NodeRunListView.axaml"));
        StringAssert.Contains(nodeXaml, "x:DataType=\"vm:NodeRunMonitorViewModel\"");
        StringAssert.Contains(nodeXaml, "ItemsSource=\"{Binding Nodes}\"");
        StringAssert.Contains(
            nodeXaml,
            "SelectedItem=\"{Binding SelectedNodeRun, Mode=TwoWay}\"");
        StringAssert.Contains(nodeXaml, "Command=\"{Binding PreviousPageCommand}\"");
        StringAssert.Contains(nodeXaml, "Command=\"{Binding NextPageCommand}\"");
        StringAssert.Contains(nodeXaml, "SelectedNodeRun.ErrorJson");
        StringAssert.Contains(nodeXaml, "Command=\"{Binding ViewTablesCommand}\"");
        StringAssert.Contains(nodeXaml, "Command=\"{Binding ViewPreviewCommand}\"");
        StringAssert.Contains(nodeXaml, "Command=\"{Binding ViewLogsCommand}\"");

        var overviewXaml = File.ReadAllText(GetViewPath("RunOverviewView.axaml"));
        StringAssert.Contains(overviewXaml, "Command=\"{Binding ViewTablesCommand}\"");
        StringAssert.Contains(overviewXaml, "Command=\"{Binding ViewPreviewCommand}\"");
        StringAssert.Contains(overviewXaml, "Command=\"{Binding ViewLogsCommand}\"");
    }

    [TestMethod]
    public void CleanupResultUsesVirtualizedBoundedLists()
    {
        var xaml = File.ReadAllText(GetViewPath("RunCleanupResultView.axaml"));
        StringAssert.Contains(xaml, "x:DataType=\"vm:BackgroundRunManagementViewModel\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding CleanedTableRefs}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding SkippedTableRefs}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding FailedTableRefs}\"");
        StringAssert.Contains(xaml, "MaxHeight=\"110\"");
        StringAssert.Contains(xaml, "MaxHeight=\"130\"");

        var detailXaml = File.ReadAllText(GetViewPath("RunDetailPanelView.axaml"));
        StringAssert.Contains(
            detailXaml,
            "DataContext=\"{Binding BackgroundRunManagement}\"");
    }

    private static bool IsWidthSafeButton(XElement button)
    {
        return (string?)button.Attribute("HorizontalAlignment") == "Stretch"
            && button.Attribute("MinWidth") is null;
    }

    private static string GetViewPath(string fileName)
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var path = Path.Combine(
                directory.FullName,
                "Avalonia_UI",
                "Views",
                "Components",
                "RunMonitor",
                fileName);
            if (File.Exists(path))
            {
                return path;
            }

            directory = directory.Parent;
        }

        throw new FileNotFoundException($"Could not locate {fileName}.");
    }

    private static string GetPagePath(string fileName)
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var path = Path.Combine(
                directory.FullName,
                "Avalonia_UI",
                "Views",
                "Pages",
                fileName);
            if (File.Exists(path))
            {
                return path;
            }

            directory = directory.Parent;
        }

        throw new FileNotFoundException($"Could not locate {fileName}.");
    }
}
