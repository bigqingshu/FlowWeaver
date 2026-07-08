using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyRefreshedTableRefs(IReadOnlyList<TableRefDto> tableRefs)
    {
        var previousSelectedTableRefId = SelectedDataPreviewTableRef?.TableRefId;
        var previousSelectedStateKey = SelectedDataPreviewState?.StateKey;
        var previousSelectedTableOptionId =
            SelectedDataPreviewTableOption?.TableRefId ?? previousSelectedTableRefId;

        TableRefs.Clear();
        foreach (var tableRef in tableRefs)
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
    }
}
