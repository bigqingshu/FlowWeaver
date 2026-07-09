using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplySuccessfulNodeDataPreviewRefresh(
        string requestedRunId,
        string requestedNodeInstanceId,
        TableRefDto tableRef,
        TableDataRowsDto rows)
    {
        LoadDataPreviewRows(rows);
        UpdateDataPreviewSource(
            requestedRunId,
            requestedNodeInstanceId,
            tableRef.LogicalTableId,
            tableRef.TableRefId,
            SelectedRun?.RunMode,
            SelectedRun?.TargetNodeInstanceId);
        DataPreviewMessage = F(
            "format.loaded_data_preview",
            rows.Rows.Length,
            rows.RowCount,
            tableRef.LogicalTableId);
    }
}
