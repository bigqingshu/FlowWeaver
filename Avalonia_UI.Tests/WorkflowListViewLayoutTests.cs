using System;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowListViewLayoutTests
{
    [TestMethod]
    public void WorkflowManagementActionsUseWidthSafeTwoRowLayout()
    {
        var document = XDocument.Load(GetWorkflowListViewPath());
        var avalonia = document.Root!.Name.Namespace;
        var actionGrid = document
            .Descendants(avalonia + "Grid")
            .Single(element =>
                (string?)element.Attribute("Grid.Row") == "3"
                && element
                    .Descendants()
                    .Any(child => child.Name.LocalName == "BackgroundRunLauncherView"));

        Assert.AreEqual("Auto,Auto", (string?)actionGrid.Attribute("RowDefinitions"));
        Assert.AreEqual("8", (string?)actionGrid.Attribute("RowSpacing"));

        var backgroundRunLauncher = actionGrid
            .Elements()
            .Single(element => element.Name.LocalName == "BackgroundRunLauncherView");
        Assert.AreEqual(
            "{Binding BackgroundRunManagement}",
            (string?)backgroundRunLauncher.Attribute("DataContext"));

        var managementGrid = actionGrid
            .Elements(avalonia + "Grid")
            .Single(element => (string?)element.Attribute("Grid.Row") == "1");
        Assert.AreEqual("*,*,*", (string?)managementGrid.Attribute("ColumnDefinitions"));
        Assert.AreEqual("8", (string?)managementGrid.Attribute("ColumnSpacing"));

        var panels = managementGrid.Elements(avalonia + "Panel").ToArray();
        Assert.HasCount(3, panels);
        CollectionAssert.AreEqual(
            new[] { "0", "1", "2" },
            panels.Select(panel => (string?)panel.Attribute("Grid.Column")).ToArray());
        Assert.IsTrue(
            panels
                .SelectMany(panel => panel.Elements(avalonia + "Button"))
                .All(button =>
                    (string?)button.Attribute("HorizontalAlignment") == "Stretch"
                    && button.Attribute("MinWidth") is null));
    }

    private static string GetWorkflowListViewPath()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var path = Path.Combine(
                directory.FullName,
                "Avalonia_UI",
                "Views",
                "Components",
                "Workflow",
                "WorkflowListView.axaml");
            if (File.Exists(path))
            {
                return path;
            }

            directory = directory.Parent;
        }

        throw new FileNotFoundException("Could not locate WorkflowListView.axaml.");
    }
}
