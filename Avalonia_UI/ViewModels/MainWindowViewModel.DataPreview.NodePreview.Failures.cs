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
}
