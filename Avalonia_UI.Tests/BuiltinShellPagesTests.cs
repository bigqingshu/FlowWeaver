using System;
using System.Linq;
using Avalonia_UI.Models;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class BuiltinShellPagesTests
{
    [TestMethod]
    public void AllReturnsExpectedBuiltInPagesInNavigationOrder()
    {
        var pages = BuiltinShellPages.All;

        CollectionAssert.AreEqual(
            new[]
            {
                ShellPageKey.Workflows,
                ShellPageKey.Runs,
                ShellPageKey.Data,
                ShellPageKey.Logs,
                ShellPageKey.Settings,
            },
            pages.Select(page => page.Key).ToArray());

        CollectionAssert.AreEqual(
            new[] { 10, 20, 30, 40, 50 },
            pages.Select(page => page.SortOrder).ToArray());

        CollectionAssert.AreEqual(
            new[]
            {
                ShellPageContentKey.Workflows,
                ShellPageContentKey.Runs,
                ShellPageContentKey.Data,
                ShellPageContentKey.Logs,
                ShellPageContentKey.Settings,
            },
            pages.Select(page => page.ContentKey).ToArray());
    }

    [TestMethod]
    public void AllKeepsHeaderPropertiesOnMainWindowViewModel()
    {
        foreach (var page in BuiltinShellPages.All)
        {
            var property = typeof(MainWindowViewModel).GetProperty(page.HeaderPropertyName);

            Assert.IsNotNull(
                property,
                $"{page.Key} header property {page.HeaderPropertyName} was not found.");
            Assert.AreEqual(
                typeof(string),
                property.PropertyType,
                $"{page.Key} header property must remain a string binding source.");
        }
    }

    [TestMethod]
    public void AllKeepsResolvablePageViewTypes()
    {
        var appAssembly = typeof(BuiltinShellPages).Assembly;

        foreach (var page in BuiltinShellPages.All)
        {
            var type = appAssembly.GetType(page.ViewTypeName);

            Assert.IsNotNull(
                type,
                $"{page.Key} view type {page.ViewTypeName} was not found.");
        }
    }

    [TestMethod]
    public void AllUsesEnabledVisibleDefaults()
    {
        foreach (var page in BuiltinShellPages.All)
        {
            Assert.IsTrue(page.IsVisible, $"{page.Key} should be visible by default.");
            Assert.IsTrue(page.IsEnabled, $"{page.Key} should be enabled by default.");
        }
    }
}
