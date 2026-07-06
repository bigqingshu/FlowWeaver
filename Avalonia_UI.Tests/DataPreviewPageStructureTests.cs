using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class DataPreviewPageStructureTests
{
    [TestMethod]
    public void DataPreviewPageSeparatesStateSelectionFromTableOptionSelection()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Pages",
            "DataPreviewPage.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding DataPreviewStateSelectorText}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding DataPreviewStates}\"");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding SelectedDataPreviewState, Mode=TwoWay}\"");
        StringAssert.Contains(xaml, "DataType=\"vm:DataPreviewStateListItemViewModel\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SummaryText}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding DataPreviewTableOptions}\"");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding SelectedDataPreviewTableOption, Mode=TwoWay}\"");
        Assert.IsFalse(
            xaml.Contains("ItemsSource=\"{Binding TableRefs}\"", StringComparison.Ordinal),
            "DataPreviewPage should not bind either selector directly to the raw TableRefs list.");
        Assert.IsFalse(
            xaml.Contains("SelectedItem=\"{Binding SelectedDataPreviewTableRef", StringComparison.Ordinal),
            "DataPreviewPage should not use the legacy shared table-ref selection for user-facing selectors.");
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
