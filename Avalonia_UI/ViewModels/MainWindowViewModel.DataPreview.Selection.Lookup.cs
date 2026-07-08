using System;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
