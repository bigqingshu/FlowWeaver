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

    private async Task LoadDataPreviewWorkbenchTablePageAsync(
        TableRefListItemViewModel? requestedTableRef,
        int offset)
    {
        if (requestedTableRef is null)
        {
            return;
        }

        var requestedTableRefId = requestedTableRef.TableRefId;
        var requestVersion = ++dataPreviewWorkbenchLoadVersion;
        IsLoadingDataPreviewWorkbench = true;
        DataPreviewWorkbenchMessage = F(
            "format.loading_data_preview_table",
            requestedTableRef.LogicalTableId);
        DataPreviewWorkbenchErrorMessage = null;

        try
        {
            var response = await _apiClient.GetTableDataRowsAsync(
                BuildSettings(),
                requestedTableRefId,
                offset: Math.Max(0, offset),
                limit: DataPreviewRowLimit,
                cancellationToken: _shutdown.Token);

            if (IsStaleDataPreviewWorkbenchRequest(requestVersion))
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                DataPreviewWorkbenchMessage = T("data_preview.workbench_load_failed");
                DataPreviewWorkbenchErrorMessage = DescribeError(response);
                return;
            }

            LoadDataPreviewWorkbenchRows(response.Data);
            LoadedDataPreviewTableRef = requestedTableRef;
            UpdateDataPreviewWorkbenchLoadedMessage();
        }
        finally
        {
            if (requestVersion == dataPreviewWorkbenchLoadVersion)
            {
                IsLoadingDataPreviewWorkbench = false;
            }
        }
    }

    private bool IsStaleDataPreviewWorkbenchRequest(int requestVersion)
    {
        return requestVersion != dataPreviewWorkbenchLoadVersion;
    }
}
