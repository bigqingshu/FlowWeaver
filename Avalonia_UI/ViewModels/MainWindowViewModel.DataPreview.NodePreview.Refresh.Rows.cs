using System.Threading.Tasks;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task<TableDataRowsDto?> TryLoadRequestedNodeRowsForDataPreviewAsync(
        string requestedRunId,
        string requestedNodeInstanceId,
        string tableRefId,
        int requestVersion,
        bool notifyResult)
    {
        var rowsResponse = await _apiClient.GetTableDataRowsAsync(
            BuildSettings(),
            tableRefId,
            offset: 0,
            limit: DataPreviewRowLimit,
            cancellationToken: _shutdown.Token);

        if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
        {
            return null;
        }

        if (!rowsResponse.Ok || rowsResponse.Data is null)
        {
            ApplyFailedNodeDataPreviewResponse(rowsResponse, notifyResult);
            return null;
        }

        return rowsResponse.Data;
    }
}
