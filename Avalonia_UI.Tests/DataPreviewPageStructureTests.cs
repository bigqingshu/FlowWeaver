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
        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding TableRefs}\"",
            "The state directory should retain unreadable table metadata.");
        Assert.IsFalse(
            xaml.Contains("SelectedItem=\"{Binding SelectedDataPreviewTableRef", StringComparison.Ordinal),
            "DataPreviewPage should not use the legacy shared table-ref selection for user-facing selectors.");
    }

    [TestMethod]
    public void SharedPublicationMembersExposeStatusPagedLoadingAndPreviewCommand()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Data",
            "SharedPublicationListView.axaml");

        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding SelectedSharedPublicationVersionMembers}\"");
        StringAssert.Contains(
            xaml,
            "SelectedItem=\"{Binding SelectedSharedPublicationVersionMember}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding LifecycleStatusText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding LogicalTableId}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding PreviewCommand}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding LoadMoreSharedPublicationVersionMembersCommand}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding ExpiresAtText}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding RefreshSharedPublicationCleanupPreviewCommand}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding CleanupSharedPublicationCommand}\"");
        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding SharedPublicationCleanupBlockers}\"");
        StringAssert.Contains(xaml, "<Button.Flyout>");
        Assert.IsFalse(xaml.Contains("Rows", StringComparison.Ordinal));
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
