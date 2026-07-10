using System.Threading;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int dataPreviewWorkbenchLoadVersion;
    private CancellationTokenSource? dataPreviewWorkbenchLoadCancellation;

    [ObservableProperty]
    private bool isLoadingDataPreviewWorkbench;

    private CancellationTokenSource BeginDataPreviewWorkbenchLoad()
    {
        CancelDataPreviewWorkbenchLoad();
        dataPreviewWorkbenchLoadCancellation =
            CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        return dataPreviewWorkbenchLoadCancellation;
    }

    private void CancelDataPreviewWorkbenchLoad()
    {
        dataPreviewWorkbenchLoadCancellation?.Cancel();
        dataPreviewWorkbenchLoadCancellation?.Dispose();
        dataPreviewWorkbenchLoadCancellation = null;
    }

    private void CancelDataPreviewWorkbenchLoadForSelectionChange()
    {
        if (dataPreviewWorkbenchLoadCancellation is not null)
        {
            dataPreviewWorkbenchLoadVersion++;
        }

        CancelDataPreviewWorkbenchLoad();
    }

    private void CompleteDataPreviewWorkbenchLoad(CancellationTokenSource request)
    {
        if (ReferenceEquals(dataPreviewWorkbenchLoadCancellation, request))
        {
            dataPreviewWorkbenchLoadCancellation = null;
        }

        request.Dispose();
    }
}
