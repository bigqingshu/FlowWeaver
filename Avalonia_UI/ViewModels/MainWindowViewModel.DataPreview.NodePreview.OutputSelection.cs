using System;
using System.Linq;
using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task SelectLatestReadableOutputNodeForRunAsync(string workflowRunId)
    {
        var tableRefsResponse = await LoadRunTableDirectoryAsync(
            workflowRunId,
            _shutdown.Token);
        if (!tableRefsResponse.Ok || tableRefsResponse.Data is null)
        {
            return;
        }

        var nodeInstanceIdsWithReadableOutput = tableRefsResponse.Data
            .Where(IsReadableTableRef)
            .Select(tableRef => tableRef.SourceNodeInstanceId)
            .Where(nodeInstanceId => !string.IsNullOrWhiteSpace(nodeInstanceId))
            .Cast<string>()
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
