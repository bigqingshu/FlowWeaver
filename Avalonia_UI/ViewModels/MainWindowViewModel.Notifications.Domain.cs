using System;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static readonly TimeSpan DefaultNotificationAutoDismissAfter =
        TimeSpan.FromSeconds(4);

    private void ShowWorkflowDefinitionNotification(
        string key,
        UiNotificationKind kind,
        bool isSticky = false)
    {
        ShowNotification(
            key,
            kind,
            WorkflowDefinitionValidationMessage,
            WorkflowDefinitionValidationErrorMessage ?? string.Empty,
            isSticky,
            DefaultNotificationAutoDismissAfter);
    }

    private void ShowConnectionNotification(UiNotificationKind kind)
    {
        ShowNotification(
            "connection.check",
            kind,
            StatusMessage,
            kind == UiNotificationKind.Error ? ErrorMessage ?? string.Empty : string.Empty,
            autoDismissAfter: DefaultNotificationAutoDismissAfter);
    }

    private void ShowWorkflowNotification(string key, UiNotificationKind kind)
    {
        ShowNotification(
            key,
            kind,
            WorkflowMessage,
            kind == UiNotificationKind.Error ? WorkflowErrorMessage ?? string.Empty : string.Empty,
            autoDismissAfter: DefaultNotificationAutoDismissAfter);
    }

    private void ShowDataPreviewNotification(UiNotificationKind kind)
    {
        ShowNotification(
            "data_preview.refresh",
            kind,
            DataPreviewMessage,
            kind == UiNotificationKind.Error ? DataPreviewErrorMessage ?? string.Empty : string.Empty,
            autoDismissAfter: DefaultNotificationAutoDismissAfter);
    }
}
