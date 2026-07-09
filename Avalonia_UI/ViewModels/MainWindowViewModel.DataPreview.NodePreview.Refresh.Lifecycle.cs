namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int BeginNodeDataPreviewRefresh(string requestedNodeInstanceId)
    {
        var requestVersion = ++dataPreviewLoadVersion;
        IsLoadingDataPreview = true;
        DataPreviewMessage = F("format.loading_data_preview", requestedNodeInstanceId);
        DataPreviewErrorMessage = null;
        return requestVersion;
    }

    private void EndNodeDataPreviewRefresh(int requestVersion)
    {
        if (requestVersion == dataPreviewLoadVersion)
        {
            IsLoadingDataPreview = false;
        }
    }
}
