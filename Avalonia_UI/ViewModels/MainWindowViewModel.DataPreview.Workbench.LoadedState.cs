using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void LoadDataPreviewWorkbenchRows(TableDataRowsDto rows, bool isDraft = false)
    {
        var gridState = DataPreviewTableGridBuilder.BuildWorkbenchState(rows);
        IsDataPreviewWorkbenchDraft = isDraft;
        dataPreviewWorkbenchLoadedColumns = gridState.Columns;
        dataPreviewWorkbenchLoadedRows = gridState.Rows;
        dataPreviewWorkbenchOriginalCellRows = gridState.OriginalCellRows;
        dataPreviewWorkbenchEditableCellRows = gridState.EditableCellRows;
        dataPreviewWorkbenchOffset = gridState.Offset;
        dataPreviewWorkbenchHasMore = gridState.HasMore;
        dataPreviewWorkbenchRowCount = gridState.RowCount;
        DataPreviewWorkbenchClipboardText = string.Empty;
        ApplyDataPreviewWorkbenchSearch();
        NotifyDataPreviewWorkbenchPagingChanged();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
    }
}
