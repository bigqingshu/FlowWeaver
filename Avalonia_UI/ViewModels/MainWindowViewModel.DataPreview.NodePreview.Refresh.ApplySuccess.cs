using System;
using System.Linq;
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
        InitializeDataPreviewWorkbenchFromNodePreview(
            requestedRunId,
            tableRef,
            rows);
        DataPreviewMessage = F(
            "format.loaded_data_preview",
            rows.Rows.Length,
            rows.RowCount,
            tableRef.LogicalTableId);
    }

    private bool CanInitializeDataPreviewWorkbenchFromNodePreview(
        string requestedRunId)
    {
        return string.Equals(
                LastStartedRunId,
                requestedRunId,
                StringComparison.Ordinal)
            && RunTableNodeRunIdFilter is null
            && LoadedDataPreviewTableRef is null
            && !IsDataPreviewWorkbenchDraft
            && !IsDataPreviewWorkbenchDirty;
    }

    private void InitializeDataPreviewWorkbenchFromNodePreview(
        string requestedRunId,
        TableRefDto tableRef,
        TableDataRowsDto rows)
    {
        if (!CanInitializeDataPreviewWorkbenchFromNodePreview(requestedRunId))
        {
            return;
        }

        var target = TableRefs.FirstOrDefault(item =>
            string.Equals(
                item.TableRefId,
                tableRef.TableRefId,
                StringComparison.Ordinal));
        if (target is null)
        {
            return;
        }

        SelectDataPreviewTableOptionByTableRefId(target.TableRefId);
        SelectedDataPreviewTableRef = target;
        LoadDataPreviewWorkbenchRows(rows);
        LoadedDataPreviewTableRef = target;
        UpdateDataPreviewWorkbenchLoadedMessage();
    }
}
