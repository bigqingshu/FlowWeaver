using System;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshTableRefs()
    {
        return CanUseEngineActions && SelectedRun is not null && !IsLoadingTableRefs;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshTableRefs))]
    private async Task RefreshTableRefsAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestVersion = ++tableRefsLoadVersion;
        IsLoadingTableRefs = true;
        TableRefMessage = F("format.loading_table_refs_for", requestedRunId);
        TableRefErrorMessage = null;

        try
        {
            var response = await _apiClient.ListTableRefsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (
                SelectedRun?.WorkflowRunId != requestedRunId
                || requestVersion != tableRefsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                var previousSelectedTableRefId = SelectedDataPreviewTableRef?.TableRefId;
                var previousSelectedStateKey = SelectedDataPreviewState?.StateKey;
                var previousSelectedTableOptionId =
                    SelectedDataPreviewTableOption?.TableRefId ?? previousSelectedTableRefId;
                TableRefs.Clear();
                foreach (var tableRef in response.Data)
                {
                    TableRefs.Add(new TableRefListItemViewModel(tableRef));
                }

                RebuildDataPreviewStates(
                    previousSelectedStateKey,
                    previousSelectedTableOptionId);
                SelectedDataPreviewTableRef = TableRefs.FirstOrDefault(
                    tableRef => tableRef.TableRefId == previousSelectedTableRefId)
                    ?? SelectedDataPreviewTableOption
                    ?? TableRefs.FirstOrDefault();

                TableRefMessage = F("format.loaded_table_refs", TableRefs.Count);
                return;
            }

            TableRefMessage = T("data.table_ref_refresh_failed");
            TableRefErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == tableRefsLoadVersion)
            {
                IsLoadingTableRefs = false;
            }
        }
    }

}
