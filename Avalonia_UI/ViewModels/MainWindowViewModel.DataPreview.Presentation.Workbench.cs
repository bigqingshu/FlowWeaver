using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public bool HasDataPreviewWorkbenchError =>
        !string.IsNullOrWhiteSpace(DataPreviewWorkbenchErrorMessage);

    public bool HasDataPreviewWorkbenchColumns => DataPreviewWorkbenchColumns.Count > 0;

    public bool HasDataPreviewWorkbenchRows => DataPreviewWorkbenchRows.Count > 0;

    public bool HasDataPreviewWorkbenchClipboardText =>
        !string.IsNullOrEmpty(DataPreviewWorkbenchClipboardText);

    public bool HasDataPreviewWorkbenchPasteText =>
        !string.IsNullOrWhiteSpace(DataPreviewWorkbenchPasteText);

    public bool IsDataPreviewWorkbenchDirty =>
        dataPreviewWorkbenchEditableCellRows.Length > 0
        && !DataPreviewTableGridBuilder.CellRowsEqual(
            dataPreviewWorkbenchOriginalCellRows,
            dataPreviewWorkbenchEditableCellRows);

    public string DataPreviewWorkbenchDirtyStateText => IsDataPreviewWorkbenchDirty
        ? T("data_preview.dirty")
        : T("data_preview.clean");

    public bool CanSaveDataPreviewWorkbenchAsDraft =>
        LoadedDataPreviewTableRef?.HasCapability("SAVE_AS") == true;

    public string DataPreviewWorkbenchSavePolicyText =>
        LoadedDataPreviewTableRef is not { } tableRef
            ? T("data_preview.save_policy_local_draft")
            : CanSaveDataPreviewWorkbenchAsDraft
                ? F(
                    "format.data_preview_save_policy_save_as",
                    tableRef.StorageKind,
                    tableRef.CapabilitiesText)
                : F(
                    "format.data_preview_save_policy_read_only",
                    tableRef.StorageKind,
                    tableRef.CapabilitiesText);

    public string DataPreviewWorkbenchPageText => F(
        "format.data_preview_workbench_page",
        dataPreviewWorkbenchLoadedRows.Length == 0 ? 0 : dataPreviewWorkbenchOffset + 1,
        dataPreviewWorkbenchOffset + dataPreviewWorkbenchLoadedRows.Length,
        dataPreviewWorkbenchRowCount);

    public bool IsDataPreviewWorkbenchBusy => IsLoadingDataPreviewWorkbench;

    public string DataPreviewWorkbenchPendingText => T("data_preview.workbench_pending");

    public string DataPreviewWorkbenchSourceText =>
        IsDataPreviewWorkbenchDraft
            ? T("data_preview.workbench_draft_source")
            : LoadedDataPreviewTableRef is not { } tableRef
            ? T("data_preview.workbench_source_not_loaded")
            : F(
                "format.data_preview_workbench_source",
                tableRef.WorkflowRunId,
                tableRef.NodeRunId,
                tableRef.LogicalTableId,
                tableRef.StorageKind);

    public string DataPreviewTableSelectorText => T("data_preview.table_selector");

    public string DataPreviewStateSelectorText => T("data_preview.state_selector");

    public string DataPreviewLoadSelectedTableText => T("data_preview.load_selected_table");

    public string DataPreviewWorkbenchRefreshText => T("data_preview.workbench_refresh");

    public string DataPreviewDetailsText => T("data_preview.details");

    public string DataPreviewSearchText => T("data_preview.search");

    public string DataPreviewSearchWatermarkText => T("data_preview.search_watermark");

    public string DataPreviewCopyTsvText => T("data_preview.copy_tsv");

    public string DataPreviewPasteText => T("data_preview.paste_text");

    public string DataPreviewPasteWatermarkText => T("data_preview.paste_watermark");

    public string DataPreviewParsePasteText => T("data_preview.parse_paste");

    public string DataPreviewRestoreDraftText => T("data_preview.restore_draft");

    public string DataPreviewSaveAsText => T("data_preview.save_as");

    public string DataPreviewPreviousPageText => T("data_preview.previous_page");

    public string DataPreviewNextPageText => T("data_preview.next_page");
}
