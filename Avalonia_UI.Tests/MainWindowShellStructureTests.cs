using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class MainWindowShellStructureTests
{
    [TestMethod]
    public void MainWindowDelegatesHeaderAndPageHostToShellComponents()
    {
        var xaml = ReadSourceFile("Avalonia_UI", "Views", "MainWindow.axaml");

        StringAssert.Contains(xaml, "<shell:ShellHeaderView />");
        StringAssert.Contains(xaml, "<shell:AppShellPageHost Grid.Row=\"1\" />");
        Assert.IsFalse(xaml.Contains("AppTitleText", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("AppSubtitleText", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ConnectionStatusView", StringComparison.Ordinal));
    }

    [TestMethod]
    public void ShellHeaderViewOwnsHeaderBindingsAndConnectionStatus()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Shell",
            "ShellHeaderView.axaml");

        StringAssert.Contains(xaml, "x:DataType=\"vm:MainWindowViewModel\"");
        StringAssert.Contains(xaml, "Text=\"{Binding AppTitleText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding AppSubtitleText}\"");
        StringAssert.Contains(xaml, "<components:ConnectionStatusView Grid.Column=\"1\" VerticalAlignment=\"Center\"/>");
        Assert.IsFalse(xaml.Contains("AppShellPageHost", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("TabControl", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("TabItem", StringComparison.Ordinal));
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
