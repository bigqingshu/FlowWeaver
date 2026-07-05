using System;
using System.Threading.Tasks;
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
        Assert.IsTrue(viewModel.HasNotificationCountdown);
        Assert.AreEqual(1d, viewModel.NotificationCountdownProgress, 0.001);
        Assert.AreEqual(1, viewModel.NotificationOpenSequence);
        Assert.AreEqual(1, viewModel.NotificationUpdateCount);
        Assert.IsNotNull(viewModel.NotificationUpdatedAt);
        Assert.HasCount(1, viewModel.RecentEvents);
        Assert.AreEqual("workflow.edit", viewModel.RecentEvents[0].Key);
        Assert.AreEqual(UiNotificationKind.Success, viewModel.RecentEvents[0].Kind);
        Assert.AreEqual("Saved", viewModel.RecentEvents[0].Title);
        Assert.AreEqual("Workflow draft saved.", viewModel.RecentEvents[0].Message);
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
        Assert.IsFalse(viewModel.HasNotificationCountdown);
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
        Assert.IsFalse(viewModel.HasNotificationCountdown);
        Assert.AreEqual(0d, viewModel.NotificationCountdownProgress, 0.001);

        viewModel.CloseNotificationCommand.Execute(null);

        Assert.IsFalse(viewModel.IsNotificationOpen);
        Assert.IsNull(viewModel.NotificationAutoDismissAfter);
    }

    [TestMethod]
    public void RecentEventsShowOneByDefaultAndFiveWhenExpanded()
    {
        var viewModel = new MainWindowViewModel();

        for (var index = 0; index < 6; index++)
        {
            viewModel.ShowNotification(
                $"event-{index}",
                UiNotificationKind.Info,
                $"Event {index}",
                string.Empty);
        }

        Assert.HasCount(6, viewModel.RecentEvents);
        Assert.HasCount(1, viewModel.VisibleRecentEvents);
        Assert.AreEqual("Event 5", viewModel.VisibleRecentEvents[0].Title);
        Assert.IsTrue(viewModel.HasMoreRecentEvents);
        Assert.AreEqual("Show 5", viewModel.RecentEventsToggleText);

        viewModel.IsRecentEventsExpanded = true;

        Assert.HasCount(5, viewModel.VisibleRecentEvents);
        Assert.AreEqual("Event 5", viewModel.VisibleRecentEvents[0].Title);
        Assert.AreEqual("Event 1", viewModel.VisibleRecentEvents[4].Title);
        Assert.AreEqual("Show 1", viewModel.RecentEventsToggleText);
    }

    [TestMethod]
    public async Task NonStickyNotificationAutoDismissesAfterCountdown()
    {
        var viewModel = new MainWindowViewModel();

        viewModel.ShowNotification(
            "workflow.saved",
            UiNotificationKind.Success,
            "Saved",
            string.Empty,
            autoDismissAfter: TimeSpan.FromMilliseconds(30));

        Assert.IsTrue(viewModel.IsNotificationOpen);
        Assert.IsTrue(viewModel.HasNotificationCountdown);

        await Task.Delay(TimeSpan.FromMilliseconds(150));

        Assert.IsFalse(viewModel.IsNotificationOpen);
        Assert.IsFalse(viewModel.HasNotificationCountdown);
        Assert.IsNull(viewModel.NotificationAutoDismissAfter);
        Assert.AreEqual(0d, viewModel.NotificationCountdownProgress, 0.001);
    }

    [TestMethod]
    public void ViewAllRecentEventsNavigatesToLogsPage()
    {
        var viewModel = new MainWindowViewModel
        {
            SelectedShellPageKey = ShellPageKey.Workflows,
        };

        viewModel.ViewAllRecentEventsCommand.Execute(null);

        Assert.AreEqual(ShellPageKey.Logs, viewModel.SelectedShellPageKey);
    }
}
