using System;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanRefreshTableRefs))]
    private async Task RefreshTableRefsAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestedNodeRunId = RunTableNodeRunIdFilter;
        var requestVersion = ++tableRefsLoadVersion;
        var requestCancellation = BeginTableRefDirectoryRequest();
        IsLoadingTableRefs = true;
        TableRefMessage = F("format.loading_table_refs_for", requestedRunId);
        TableRefErrorMessage = null;

        try
        {
            runMetadataCache.InvalidateRun(requestedRunId);
            var response = await LoadRunTableDirectoryAsync(
                requestedRunId,
                requestCancellation.Token,
                requestedNodeRunId);

            if (
                SelectedRun?.WorkflowRunId != requestedRunId
                || !string.Equals(
                    RunTableNodeRunIdFilter,
                    requestedNodeRunId,
                    StringComparison.Ordinal)
                || requestVersion != tableRefsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                ApplyRefreshedTableRefs(response.Data);
                TableRefMessage = requestedNodeRunId is null
                    ? F("format.loaded_table_refs", TableRefs.Count)
                    : F(
                        "format.loaded_node_table_refs",
                        TableRefs.Count,
                        requestedNodeRunId);
                return;
            }

            TableRefMessage = T("data.table_ref_refresh_failed");
            TableRefErrorMessage = DescribeError(response);
        }
        catch (OperationCanceledException) when (requestCancellation.IsCancellationRequested)
        {
        }
        finally
        {
            if (requestVersion == tableRefsLoadVersion)
            {
                IsLoadingTableRefs = false;
            }

            CompleteTableRefDirectoryRequest(requestCancellation);
        }
    }
}
