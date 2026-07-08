using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task<bool> TryRefreshSelectedWorkflowNodeDataPreviewAsync(
        bool notifyResult = true)
    {
        if (SelectedRun is null || SelectedWorkflowDefinitionNode is null)
        {
            return false;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestedNodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        var requestVersion = BeginNodeDataPreviewRefresh(requestedNodeInstanceId);

        try
        {
            var nodeRunsResponse = await _apiClient.ListNodeRunsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
            {
                return false;
            }

            if (!nodeRunsResponse.Ok || nodeRunsResponse.Data is null)
            {
                return ApplyFailedNodeDataPreviewResponse(nodeRunsResponse, notifyResult);
            }

            var nodeRun = FindNodeRunByInstanceId(
                nodeRunsResponse.Data,
                requestedNodeInstanceId);
            if (nodeRun is null)
            {
                return ApplyMissingNodeDataPreviewOutput(
                    "format.data_preview_node_run_not_found",
                    requestedNodeInstanceId,
                    notifyResult);
            }

            var tableRefsResponse = await _apiClient.ListTableRefsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
            {
                return false;
            }

            if (!tableRefsResponse.Ok || tableRefsResponse.Data is null)
            {
                return ApplyFailedNodeDataPreviewResponse(tableRefsResponse, notifyResult);
            }

            var tableRef = FindLatestReadableNodeRunTableRef(
                tableRefsResponse.Data,
                nodeRun.NodeRunId);
            if (tableRef is null)
            {
                return ApplyMissingNodeDataPreviewOutput(
                    "format.data_preview_table_ref_not_found",
                    requestedNodeInstanceId,
                    notifyResult);
            }

            var rowsResponse = await _apiClient.GetTableDataRowsAsync(
                BuildSettings(),
                tableRef.TableRefId,
                offset: 0,
                limit: DataPreviewRowLimit,
                cancellationToken: _shutdown.Token);

            if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
            {
                return false;
            }

            if (!rowsResponse.Ok || rowsResponse.Data is null)
            {
                return ApplyFailedNodeDataPreviewResponse(rowsResponse, notifyResult);
            }

            ApplySuccessfulNodeDataPreviewRefresh(
                requestedRunId,
                requestedNodeInstanceId,
                tableRef,
                rowsResponse.Data);
            if (notifyResult)
            {
                ShowDataPreviewNotification(UiNotificationKind.Success);
            }

            return true;
        }
        finally
        {
            EndNodeDataPreviewRefresh(requestVersion);
        }
    }
}
