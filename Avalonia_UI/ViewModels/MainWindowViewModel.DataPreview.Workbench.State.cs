using System.Collections.ObjectModel;
using Avalonia_UI.Models;
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

    [ObservableProperty]
    private string dataPreviewWorkbenchSearchText = string.Empty;

    [ObservableProperty]
    private string dataPreviewWorkbenchClipboardText = string.Empty;

    [ObservableProperty]
    private string dataPreviewWorkbenchPasteText = string.Empty;

    [ObservableProperty]
    private bool isDataPreviewWorkbenchDraft;

    public ObservableCollection<TableDataPreviewColumnViewModel> DataPreviewWorkbenchColumns { get; } = new();

    public ObservableCollection<TableDataPreviewRowViewModel> DataPreviewWorkbenchRows { get; } =
        new();

}
