using System.Threading.Tasks;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task<NodeRunDto?> TryLoadRequestedNodeRunForDataPreviewAsync(
        string requestedRunId,
        string requestedNodeInstanceId,
        int requestVersion,
        bool notifyResult)
    {
        var nodeRunsResponse = await _apiClient.ListNodeRunsAsync(
            BuildSettings(),
            requestedRunId,
            _shutdown.Token);

        if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
        {
            return null;
        }

        if (!nodeRunsResponse.Ok || nodeRunsResponse.Data is null)
        {
            ApplyFailedNodeDataPreviewResponse(nodeRunsResponse, notifyResult);
            return null;
        }

        var nodeRun = FindNodeRunByInstanceId(
            nodeRunsResponse.Data,
            requestedNodeInstanceId);
        if (nodeRun is null)
        {
            ApplyMissingNodeDataPreviewOutput(
                "format.data_preview_node_run_not_found",
                requestedNodeInstanceId,
                notifyResult);
        }

        return nodeRun;
    }
}
