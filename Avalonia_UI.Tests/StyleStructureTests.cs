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
    public void ControlStylesOwnButtonAndCardStyles()
    {
        var xaml = ReadSourceFile("Avalonia_UI", "Styles", "ControlStyles.axaml");

        StringAssert.Contains(xaml, "<Styles xmlns=\"https://github.com/avaloniaui\">");
        StringAssert.Contains(xaml, "Selector=\"Button\"");
        StringAssert.Contains(xaml, "Selector=\"Button:pointerover /template/ ContentPresenter\"");
        StringAssert.Contains(xaml, "Selector=\"Button:pressed /template/ ContentPresenter\"");
        StringAssert.Contains(xaml, "Selector=\"Button.Primary\"");
        StringAssert.Contains(xaml, "Selector=\"Button.Primary:pointerover /template/ ContentPresenter\"");
        StringAssert.Contains(xaml, "Selector=\"Button.Primary:pressed /template/ ContentPresenter\"");
        StringAssert.Contains(xaml, "Selector=\"Border.Card\"");
    }

    [TestMethod]
    public void MainWindowNoLongerOwnsFirstControlStyleBatch()
    {
        var xaml = ReadSourceFile("Avalonia_UI", "Views", "MainWindow.axaml");

        Assert.IsFalse(xaml.Contains("Selector=\"Button\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("Selector=\"Button.Primary\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("Selector=\"Border.Card\"", StringComparison.Ordinal));
        StringAssert.Contains(xaml, "Selector=\"ListBoxItem\"");
        StringAssert.Contains(xaml, "Selector=\"TabControl\"");
        StringAssert.Contains(xaml, "Selector=\"TabItem\"");
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
