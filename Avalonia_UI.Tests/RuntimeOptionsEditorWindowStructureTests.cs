using System;
using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class RuntimeOptionsEditorWindowStructureTests
{
    [TestMethod]
    public void CompatibilityOnlyFieldsAreNotEditableControls()
    {
        var xaml = File.ReadAllText(Path.Combine(
            GetRepoRoot(),
            "Avalonia_UI",
            "Views",
            "Windows",
            "RuntimeOptionsEditorWindow.axaml"));

        Assert.IsFalse(xaml.Contains(
            "RuntimeOptionsStrictValidationDraft",
            StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains(
            "RuntimeOptionsSelectedNodeStrictValidationDraft",
            StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains(
            "RuntimeOptionsTtlSecondsDraft",
            StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains(
            "RuntimeOptionsSelectedNodeTtlSecondsDraft",
            StringComparison.Ordinal));
    }

    private static string GetRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI")) &&
                Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI.Tests")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException(
            "Could not locate FlowWeaver repository root.");
    }
}
