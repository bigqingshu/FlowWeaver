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

    private void RebuildDataPreviewStates(
        string? preferredStateKey = null,
        string? preferredTableRefId = null)
    {
        DataPreviewStates.Clear();
        foreach (var state in DataPreviewStateListItemViewModel.FromTableRefs(TableRefs))
        {
            DataPreviewStates.Add(state);
        }

        var selectedState =
            FindDataPreviewStateByKey(preferredStateKey)
            ?? FindDataPreviewStateByTableRefId(preferredTableRefId)
            ?? DataPreviewStates.FirstOrDefault();
        SelectedDataPreviewState = selectedState;

        if (!string.IsNullOrWhiteSpace(preferredTableRefId))
        {
            SelectedDataPreviewTableOption =
                DataPreviewTableOptions.FirstOrDefault(tableRef =>
                    string.Equals(tableRef.TableRefId, preferredTableRefId, StringComparison.Ordinal))
                ?? SelectedDataPreviewTableOption;
        }
    }

    private DataPreviewStateListItemViewModel? FindDataPreviewStateByKey(string? stateKey)
    {
        return string.IsNullOrWhiteSpace(stateKey)
            ? null
            : DataPreviewStates.FirstOrDefault(state =>
                string.Equals(state.StateKey, stateKey, StringComparison.Ordinal));
    }

    private DataPreviewStateListItemViewModel? FindDataPreviewStateByTableRefId(string? tableRefId)
    {
        return string.IsNullOrWhiteSpace(tableRefId)
            ? null
            : DataPreviewStates.FirstOrDefault(state =>
                state.TableRefs.Any(tableRef =>
                    string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal)));
    }

    private void SelectDataPreviewTableOptionByTableRefId(string? tableRefId)
    {
        var state = FindDataPreviewStateByTableRefId(tableRefId);
        if (state is null)
        {
            return;
        }

        SelectedDataPreviewState = state;
        SelectedDataPreviewTableOption =
            DataPreviewTableOptions.FirstOrDefault(tableRef =>
                string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal))
            ?? SelectedDataPreviewTableOption;
    }

    partial void OnSelectedDataPreviewStateChanged(DataPreviewStateListItemViewModel? value)
    {
        var previousTableRefId = SelectedDataPreviewTableOption?.TableRefId;
        DataPreviewTableOptions.Clear();
        if (value is not null)
        {
            foreach (var tableRef in value.TableRefs)
            {
                DataPreviewTableOptions.Add(tableRef);
            }
        }

        SelectedDataPreviewTableOption =
            DataPreviewTableOptions.FirstOrDefault(tableRef =>
                string.Equals(tableRef.TableRefId, previousTableRefId, StringComparison.Ordinal))
            ?? DataPreviewTableOptions.FirstOrDefault();
    }

    partial void OnSelectedDataPreviewTableOptionChanged(TableRefListItemViewModel? value)
    {
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedDataPreviewTableRefChanged(TableRefListItemViewModel? value)
    {
        DataPreviewWorkbenchErrorMessage = null;
        if (value is not null)
        {
            SelectDataPreviewTableOptionByTableRefId(value.TableRefId);
        }

        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }
}
