using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool ApplyFailedNodeDataPreviewResponse<TData>(
        ApiResponseEnvelope<TData> response,
        bool notifyResult)
    {
        DataPreviewMessage = T("data_preview.refresh_failed");
        DataPreviewErrorMessage = DescribeError(response);
        if (notifyResult)
        {
            ShowDataPreviewNotification(UiNotificationKind.Error);
        }

        return false;
    }

    private bool ApplyMissingNodeDataPreviewOutput(
        string messageKey,
        string nodeInstanceId,
        bool notifyResult)
    {
        DataPreviewMessage = F(messageKey, nodeInstanceId);
        if (notifyResult)
        {
            ShowDataPreviewNotification(UiNotificationKind.Warning);
        }

        return false;
    }
}
