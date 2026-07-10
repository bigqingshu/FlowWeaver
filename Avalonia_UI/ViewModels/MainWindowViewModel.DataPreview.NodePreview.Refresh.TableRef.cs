using System.Threading.Tasks;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task<TableRefDto?> TryLoadRequestedNodeTableRefForDataPreviewAsync(
        string requestedRunId,
        string requestedNodeInstanceId,
        int requestVersion,
        bool notifyResult)
    {
        var tableRefsResponse = await LoadRunTableDirectoryAsync(
            requestedRunId,
            _shutdown.Token);

        if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
        {
            return null;
        }

        if (!tableRefsResponse.Ok || tableRefsResponse.Data is null)
        {
            ApplyFailedNodeDataPreviewResponse(tableRefsResponse, notifyResult);
            return null;
        }

        var tableRef = FindLatestReadableNodeTableRef(
            tableRefsResponse.Data,
            requestedNodeInstanceId);
        if (tableRef is null)
        {
            ApplyMissingNodeDataPreviewOutput(
                "format.data_preview_table_ref_not_found",
                requestedNodeInstanceId,
                notifyResult);
        }

        return tableRef;
    }
}
