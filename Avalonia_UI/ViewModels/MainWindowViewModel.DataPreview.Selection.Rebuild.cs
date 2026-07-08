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
}
