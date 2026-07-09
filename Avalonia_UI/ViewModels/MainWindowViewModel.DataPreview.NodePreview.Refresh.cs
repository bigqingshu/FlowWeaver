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
            var nodeRun = await TryLoadRequestedNodeRunForDataPreviewAsync(
                requestedRunId,
                requestedNodeInstanceId,
                requestVersion,
                notifyResult);
            if (nodeRun is null)
            {
                return false;
            }

            var tableRef = await TryLoadRequestedNodeTableRefForDataPreviewAsync(
                requestedRunId,
                requestedNodeInstanceId,
                nodeRun.NodeRunId,
                requestVersion,
                notifyResult);
            if (tableRef is null)
            {
                return false;
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
