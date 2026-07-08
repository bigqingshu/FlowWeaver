using System;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
