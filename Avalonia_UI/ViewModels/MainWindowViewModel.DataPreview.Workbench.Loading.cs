using System;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanLoadSelectedDataPreviewTable))]
    private async Task LoadSelectedDataPreviewTableAsync()
    {
        await LoadDataPreviewWorkbenchTablePageAsync(SelectedDataPreviewTableOption, 0);
    }

    [RelayCommand(CanExecute = nameof(CanLoadPreviousDataPreviewWorkbenchPage))]
    private async Task LoadPreviousDataPreviewWorkbenchPageAsync()
    {
        await LoadDataPreviewWorkbenchTablePageAsync(
            LoadedDataPreviewTableRef,
            Math.Max(0, dataPreviewWorkbenchOffset - DataPreviewRowLimit));
    }

    [RelayCommand(CanExecute = nameof(CanLoadNextDataPreviewWorkbenchPage))]
    private async Task LoadNextDataPreviewWorkbenchPageAsync()
    {
        await LoadDataPreviewWorkbenchTablePageAsync(
            LoadedDataPreviewTableRef,
            dataPreviewWorkbenchOffset + DataPreviewRowLimit);
    }

    private bool IsStaleDataPreviewWorkbenchRequest(int requestVersion)
    {
        return requestVersion != dataPreviewWorkbenchLoadVersion;
    }
}
