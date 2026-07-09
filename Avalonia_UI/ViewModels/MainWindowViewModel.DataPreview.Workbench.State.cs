using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int dataPreviewWorkbenchLoadVersion;

    [ObservableProperty]
    private TableRefListItemViewModel? loadedDataPreviewTableRef;

    [ObservableProperty]
    private bool isLoadingDataPreviewWorkbench;

    [ObservableProperty]
    private string dataPreviewWorkbenchMessage =
        "Select a run, refresh table refs, then select a table to inspect rows.";

    [ObservableProperty]
    private string? dataPreviewWorkbenchErrorMessage;
}
