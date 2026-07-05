using System;
using Avalonia_UI.Models;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class MainWindowViewModelNotificationTests
{
    [TestMethod]
    public void ShowNotificationOpensAndUpdatesState()
    {
        var viewModel = new MainWindowViewModel();

        viewModel.ShowNotification(
            "workflow.edit",
            UiNotificationKind.Success,
            "Saved",
            "Workflow draft saved.",
            autoDismissAfter: TimeSpan.FromSeconds(3));

        Assert.IsTrue(viewModel.IsNotificationOpen);
        Assert.AreEqual("workflow.edit", viewModel.NotificationKey);
        Assert.AreEqual(UiNotificationKind.Success, viewModel.NotificationKind);
        Assert.AreEqual("Success", viewModel.NotificationKindText);
        Assert.AreEqual("Saved", viewModel.NotificationTitle);
        Assert.AreEqual("Workflow draft saved.", viewModel.NotificationMessage);
        Assert.IsFalse(viewModel.IsNotificationSticky);
        Assert.AreEqual(TimeSpan.FromSeconds(3), viewModel.NotificationAutoDismissAfter);
        Assert.AreEqual(1, viewModel.NotificationOpenSequence);
        Assert.AreEqual(1, viewModel.NotificationUpdateCount);
        Assert.IsNotNull(viewModel.NotificationUpdatedAt);
    }

    [TestMethod]
    public void ShowNotificationWithSameKeyUpdatesWithoutNewOpenSequence()
    {
        var viewModel = new MainWindowViewModel();

        viewModel.ShowNotification(
            "workflow.edit",
            UiNotificationKind.Info,
            "Saving",
            "Saving draft.");
        var openSequence = viewModel.NotificationOpenSequence;

        viewModel.ShowNotification(
            "workflow.edit",
            UiNotificationKind.Success,
            "Saved",
            "Draft saved.");

        Assert.IsTrue(viewModel.IsNotificationOpen);
        Assert.AreEqual(openSequence, viewModel.NotificationOpenSequence);
        Assert.AreEqual(2, viewModel.NotificationUpdateCount);
        Assert.AreEqual(UiNotificationKind.Success, viewModel.NotificationKind);
        Assert.AreEqual("Saved", viewModel.NotificationTitle);
        Assert.AreEqual("Draft saved.", viewModel.NotificationMessage);
    }

    [TestMethod]
    public void ShowNotificationWithNewKeyStartsNewOpenSequence()
    {
        var viewModel = new MainWindowViewModel();

        viewModel.ShowNotification(
            "workflow.edit",
            UiNotificationKind.Info,
            "Saving",
            "Saving draft.");
        var openSequence = viewModel.NotificationOpenSequence;

        viewModel.ShowNotification(
            "workflow.run",
            UiNotificationKind.Info,
            "Running",
            "Workflow started.");

        Assert.IsGreaterThan(openSequence, viewModel.NotificationOpenSequence);
        Assert.AreEqual("workflow.run", viewModel.NotificationKey);
    }

    [TestMethod]
    public void ErrorNotificationIsStickyUntilClosed()
    {
        var viewModel = new MainWindowViewModel();

        viewModel.ShowNotification(
            "workflow.save.error",
            UiNotificationKind.Error,
            "Save failed",
            "Revision conflict.",
            autoDismissAfter: TimeSpan.FromSeconds(3));

        Assert.IsTrue(viewModel.IsNotificationSticky);
        Assert.IsNull(viewModel.NotificationAutoDismissAfter);

        viewModel.CloseNotificationCommand.Execute(null);

        Assert.IsFalse(viewModel.IsNotificationOpen);
        Assert.IsNull(viewModel.NotificationAutoDismissAfter);
    }
}
