using System;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RebuildDataPreviewStates()
    {
        DataPreviewStates.Clear();
        foreach (var state in DataPreviewStateListItemViewModel.FromTableRefs(TableRefs))
        {
            DataPreviewStates.Add(state);
        }

        var selection = dataPreviewSelectionState.Resolve(
            DataPreviewStates
                .Select(state => new DataPreviewStateSelectionCandidate(
                    state.StateKey,
                    state.TableRefs
                        .Select(tableRef => tableRef.TableRefId)
                        .ToArray()))
                .ToArray());
        SelectedDataPreviewState = FindDataPreviewStateByKey(selection.StateKey);

        if (!string.IsNullOrWhiteSpace(selection.TableRefId))
        {
            SelectedDataPreviewTableOption =
                DataPreviewTableOptions.FirstOrDefault(tableRef =>
                    string.Equals(
                        tableRef.TableRefId,
                        selection.TableRefId,
                        StringComparison.Ordinal))
                ?? SelectedDataPreviewTableOption;
        }
    }
}
