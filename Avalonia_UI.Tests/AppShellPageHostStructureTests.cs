using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class AppShellPageHostStructureTests
{
    [TestMethod]
    public void MainWindowDelegatesPageContentToAppShellPageHost()
    {
        var xaml = ReadSourceFile("Avalonia_UI", "Views", "MainWindow.axaml");

        StringAssert.Contains(xaml, "<shell:AppShellPageHost Grid.Row=\"1\" />");
        Assert.IsFalse(xaml.Contains("<pages:WorkflowPage", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("<pages:RunMonitorPage", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("<pages:DataPage", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("<pages:LogsAuditPage", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("<pages:SettingsPage", StringComparison.Ordinal));
    }

    [TestMethod]
    public void AppShellPageHostKeepsFixedPagesAndNavigationHeaders()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Shell",
            "AppShellPageHost.axaml");

        StringAssert.Contains(xaml, "<TabControl TabStripPlacement=\"Left\"");
        StringAssert.Contains(xaml, "SelectedIndex=\"{Binding SelectedShellPageIndex, Mode=TwoWay}\"");
        StringAssert.Contains(xaml, "Header=\"{Binding WorkflowsNavigationItem.HeaderText}\"");
        StringAssert.Contains(xaml, "Header=\"{Binding RunsNavigationItem.HeaderText}\"");
        StringAssert.Contains(xaml, "Header=\"{Binding DataNavigationItem.HeaderText}\"");
        StringAssert.Contains(xaml, "Header=\"{Binding LogsNavigationItem.HeaderText}\"");
        StringAssert.Contains(xaml, "Header=\"{Binding SettingsNavigationItem.HeaderText}\"");
        StringAssert.Contains(xaml, "<pages:WorkflowPage />");
        StringAssert.Contains(xaml, "<pages:RunMonitorPage />");
        StringAssert.Contains(xaml, "<pages:DataPage />");
        StringAssert.Contains(xaml, "<pages:LogsAuditPage />");
        StringAssert.Contains(xaml, "<pages:SettingsPage />");
        Assert.IsFalse(xaml.Contains("ItemsSource=", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ContentTemplate", StringComparison.Ordinal));
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
