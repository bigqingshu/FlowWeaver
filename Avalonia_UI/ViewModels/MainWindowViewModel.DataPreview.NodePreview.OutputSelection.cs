using System;
using System.Linq;
using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task SelectLatestReadableOutputNodeForRunAsync(string workflowRunId)
    {
        var nodeRunsResponse = await _apiClient.ListNodeRunsAsync(
            BuildSettings(),
            workflowRunId,
            _shutdown.Token);
        if (!nodeRunsResponse.Ok || nodeRunsResponse.Data is null)
        {
            return;
        }

        var tableRefsResponse = await _apiClient.ListTableRefsAsync(
            BuildSettings(),
            workflowRunId,
            _shutdown.Token);
        if (!tableRefsResponse.Ok || tableRefsResponse.Data is null)
        {
            return;
        }

        var nodeInstanceIdsWithReadableOutput = tableRefsResponse.Data
            .Where(IsReadablePublishedTableRef)
            .Join(
                nodeRunsResponse.Data,
                tableRef => tableRef.NodeRunId,
                nodeRun => nodeRun.NodeRunId,
                (_, nodeRun) => nodeRun.NodeInstanceId)
            .ToHashSet(StringComparer.Ordinal);
        var latestOutputNode = WorkflowDefinitionDraftNodes
            .Reverse()
            .FirstOrDefault(node => nodeInstanceIdsWithReadableOutput.Contains(node.NodeInstanceId));
        if (latestOutputNode is not null)
        {
            SelectedWorkflowDefinitionNode = latestOutputNode;
        }
    }
}
