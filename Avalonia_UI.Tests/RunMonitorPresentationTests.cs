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
        Assert.AreEqual("*,*,*", (string?)grids[1].Attribute("ColumnDefinitions"));

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
        Assert.HasCount(3, actionButtons);
        Assert.IsTrue(actionButtons.All(IsWidthSafeButton));

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
