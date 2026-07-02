using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class StyleStructureTests
{
    [TestMethod]
    public void AppIncludesColorPaletteResourcesAndControlStyles()
    {
        var xaml = ReadSourceFile("Avalonia_UI", "App.axaml");

        StringAssert.Contains(
            xaml,
            "ResourceInclude Source=\"avares://Avalonia_UI/Styles/ColorPalette.axaml\"");
        StringAssert.Contains(
            xaml,
            "StyleInclude Source=\"avares://Avalonia_UI/Styles/ControlStyles.axaml\"");
    }

    [TestMethod]
    public void ControlStylesOwnMigratedControlStyles()
    {
        var xaml = ReadSourceFile("Avalonia_UI", "Styles", "ControlStyles.axaml");

        StringAssert.Contains(xaml, "<Styles xmlns=\"https://github.com/avaloniaui\">");
        StringAssert.Contains(xaml, "Selector=\"Button\"");
        StringAssert.Contains(xaml, "Selector=\"Button:pointerover /template/ ContentPresenter\"");
        StringAssert.Contains(xaml, "Selector=\"Button:pressed /template/ ContentPresenter\"");
        StringAssert.Contains(xaml, "Selector=\"Button.Primary\"");
        StringAssert.Contains(xaml, "Selector=\"Button.Primary:pointerover /template/ ContentPresenter\"");
        StringAssert.Contains(xaml, "Selector=\"Button.Primary:pressed /template/ ContentPresenter\"");
        StringAssert.Contains(xaml, "Selector=\"ListBoxItem\"");
        StringAssert.Contains(xaml, "Selector=\"ListBoxItem:pointerover\"");
        StringAssert.Contains(xaml, "Selector=\"ListBoxItem:selected\"");
        StringAssert.Contains(xaml, "Selector=\"Border.Card\"");
    }

    [TestMethod]
    public void MainWindowNoLongerOwnsFirstControlStyleBatch()
    {
        var xaml = ReadSourceFile("Avalonia_UI", "Views", "MainWindow.axaml");

        Assert.IsFalse(xaml.Contains("Selector=\"Button\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("Selector=\"Button.Primary\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("Selector=\"ListBoxItem\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("Selector=\"ListBoxItem:pointerover\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("Selector=\"ListBoxItem:selected\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("Selector=\"Border.Card\"", StringComparison.Ordinal));
    }

    [TestMethod]
    public void MainWindowStillOwnsCombinedShellRegionStyles()
    {
        var appXaml = ReadSourceFile("Avalonia_UI", "App.axaml");
        var controlStylesXaml = ReadSourceFile("Avalonia_UI", "Styles", "ControlStyles.axaml");
        var mainWindowXaml = ReadSourceFile("Avalonia_UI", "Views", "MainWindow.axaml");

        Assert.IsFalse(appXaml.Contains("ShellStyles.axaml", StringComparison.Ordinal));
        Assert.IsFalse(controlStylesXaml.Contains("Selector=\"TabControl\"", StringComparison.Ordinal));
        Assert.IsFalse(controlStylesXaml.Contains("Selector=\"TabItem\"", StringComparison.Ordinal));
        StringAssert.Contains(mainWindowXaml, "Selector=\"TabControl\"");
        StringAssert.Contains(
            mainWindowXaml,
            "Selector=\"TabControl[TabStripPlacement=Left] /template/ ContentPresenter#PART_SelectedContentHost\"");
        StringAssert.Contains(
            mainWindowXaml,
            "Selector=\"TabControl[TabStripPlacement=Left] /template/ ItemsPresenter#PART_ItemsPresenter\"");
        StringAssert.Contains(mainWindowXaml, "Selector=\"TabItem\"");
        StringAssert.Contains(mainWindowXaml, "Selector=\"TabItem > TextBlock\"");
        StringAssert.Contains(
            mainWindowXaml,
            "Selector=\"TabItem:pointerover /template/ Border#PART_LayoutRoot\"");
        StringAssert.Contains(
            mainWindowXaml,
            "Selector=\"TabItem:pointerover /template/ ContentPresenter\"");
        StringAssert.Contains(mainWindowXaml, "Selector=\"TabItem:pointerover\"");
        StringAssert.Contains(
            mainWindowXaml,
            "Selector=\"TabItem:selected /template/ ContentPresenter\"");
        StringAssert.Contains(mainWindowXaml, "Selector=\"TabItem:selected\"");
        StringAssert.Contains(
            mainWindowXaml,
            "Selector=\"TabItem:selected /template/ Border#PART_SelectedPipe\"");
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
