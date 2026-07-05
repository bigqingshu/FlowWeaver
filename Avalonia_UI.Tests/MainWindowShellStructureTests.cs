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
        StringAssert.Contains(xaml, "<shell:ShellNotificationHostView Grid.Row=\"1\"");
        StringAssert.Contains(xaml, "VerticalAlignment=\"Top\"");
        StringAssert.Contains(xaml, "Margin=\"0,12,12,0\"");
        StringAssert.Contains(xaml, "ZIndex=\"10\"");
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

    [TestMethod]
    public void ShellNotificationHostOwnsNotificationOverlayBindings()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Shell",
            "ShellNotificationHostView.axaml");

        StringAssert.Contains(xaml, "x:DataType=\"vm:MainWindowViewModel\"");
        StringAssert.Contains(xaml, "Width=\"420\"");
        StringAssert.Contains(xaml, "MaxHeight=\"220\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsNotificationOpen}\"");
        StringAssert.Contains(xaml, "ColumnDefinitions=\"Auto,*\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NotificationKindText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NotificationTitle}\"");
        StringAssert.Contains(xaml, "TextWrapping=\"Wrap\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NotificationMessage}\"");
        StringAssert.Contains(xaml, "<ScrollViewer Grid.Row=\"1\"");
        StringAssert.Contains(xaml, "MaxHeight=\"140\"");
        StringAssert.Contains(xaml, "Command=\"{Binding CloseNotificationCommand}\"");
        Assert.IsFalse(xaml.Contains("Orientation=\"Horizontal\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("RuntimeEvent", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("AuditEvent", StringComparison.Ordinal));
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
