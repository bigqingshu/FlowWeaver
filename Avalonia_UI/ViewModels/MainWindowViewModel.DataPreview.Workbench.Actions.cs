using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanCopyDataPreviewWorkbenchTsv))]
    private void CopyDataPreviewWorkbenchTsv()
    {
        DataPreviewWorkbenchClipboardText = BuildDataPreviewWorkbenchTsv();
    }

    [RelayCommand(CanExecute = nameof(CanParseDataPreviewWorkbenchPaste))]
    private void ParseDataPreviewWorkbenchPaste()
    {
        DataPreviewWorkbenchErrorMessage = null;
        if (!DataPreviewTableGridBuilder.TryParseDelimitedTable(
                DataPreviewWorkbenchPasteText,
                out var columns,
                out var rows,
                out var errorKey))
        {
            DataPreviewWorkbenchMessage = T("data_preview.workbench_parse_failed");
            DataPreviewWorkbenchErrorMessage = errorKey is null ? null : T(errorKey);
            return;
        }

        LoadedDataPreviewTableRef = null;
        LoadDataPreviewWorkbenchRows(
            new TableDataRowsDto
            {
                TableRefId = "local-draft",
                Offset = 0,
                Limit = rows.Length,
                RowCount = rows.Length,
                Columns = columns,
                Rows = rows,
                HasMore = false,
            },
            isDraft: true);
        DataPreviewWorkbenchMessage = F(
            "format.data_preview_imported_rows",
            rows.Length,
            columns.Length);
    }

    [RelayCommand(CanExecute = nameof(CanRestoreDataPreviewWorkbenchDraft))]
    private void RestoreDataPreviewWorkbenchDraft()
    {
        dataPreviewWorkbenchEditableCellRows =
            DataPreviewTableGridBuilder.CloneCellRows(dataPreviewWorkbenchOriginalCellRows);
        ApplyDataPreviewWorkbenchSearch();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
        DataPreviewWorkbenchClipboardText = string.Empty;
        DataPreviewWorkbenchMessage = T("data_preview.draft_restored");
    }

    [RelayCommand(CanExecute = nameof(CanSaveDataPreviewWorkbenchAs))]
    private void SaveDataPreviewWorkbenchAs()
    {
        DataPreviewWorkbenchMessage = T("data_preview.save_as_api_pending");
        DataPreviewWorkbenchErrorMessage = null;
    }
}
