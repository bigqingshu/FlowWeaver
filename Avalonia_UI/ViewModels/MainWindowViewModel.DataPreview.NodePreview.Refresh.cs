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
            runMetadataCache.InvalidateRun(requestedRunId);
            var tableRef = await TryLoadRequestedNodeTableRefForDataPreviewAsync(
                requestedRunId,
                requestedNodeInstanceId,
                requestVersion,
                notifyResult);
            if (tableRef is null)
            {
                return false;
            }

            var rows = await TryLoadRequestedNodeRowsForDataPreviewAsync(
                requestedRunId,
                requestedNodeInstanceId,
                tableRef.TableRefId,
                requestVersion,
                notifyResult);
            if (rows is null)
            {
                return false;
            }

            ApplySuccessfulNodeDataPreviewRefresh(
                requestedRunId,
                requestedNodeInstanceId,
                tableRef,
                rows);
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
