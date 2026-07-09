using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
            CreateDataPreviewWorkbenchDraftRows(columns, rows),
            isDraft: true);
        DataPreviewWorkbenchMessage = F(
            "format.data_preview_imported_rows",
            rows.Length,
            columns.Length);
    }

}
