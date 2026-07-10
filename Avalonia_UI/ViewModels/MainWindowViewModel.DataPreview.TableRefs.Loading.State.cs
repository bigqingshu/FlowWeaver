using System.Threading;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int tableRefsLoadVersion;
    private CancellationTokenSource? tableRefsLoadCancellation;

    [ObservableProperty]
    private bool isLoadingTableRefs;

    private CancellationTokenSource BeginTableRefDirectoryRequest()
    {
        CancelTableRefDirectoryRequest();
        tableRefsLoadCancellation = CancellationTokenSource.CreateLinkedTokenSource(
            _shutdown.Token);
        return tableRefsLoadCancellation;
    }

    private void CancelTableRefDirectoryRequest()
    {
        tableRefsLoadCancellation?.Cancel();
        tableRefsLoadCancellation?.Dispose();
        tableRefsLoadCancellation = null;
    }

    private void CompleteTableRefDirectoryRequest(CancellationTokenSource request)
    {
        if (ReferenceEquals(tableRefsLoadCancellation, request))
        {
            tableRefsLoadCancellation = null;
        }

        request.Dispose();
    }
}
