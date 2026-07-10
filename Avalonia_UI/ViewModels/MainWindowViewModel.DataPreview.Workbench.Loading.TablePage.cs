using System;
using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
        var requestCancellation = BeginDataPreviewWorkbenchLoad();
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
                cancellationToken: requestCancellation.Token);

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
        catch (OperationCanceledException) when (requestCancellation.IsCancellationRequested)
        {
        }
        finally
        {
            if (requestVersion == dataPreviewWorkbenchLoadVersion)
            {
                IsLoadingDataPreviewWorkbench = false;
            }

            CompleteDataPreviewWorkbenchLoad(requestCancellation);
        }
    }
}
