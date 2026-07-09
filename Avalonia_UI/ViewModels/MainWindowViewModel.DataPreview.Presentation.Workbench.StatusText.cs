namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public string DataPreviewWorkbenchDirtyStateText => IsDataPreviewWorkbenchDirty
        ? T("data_preview.dirty")
        : T("data_preview.clean");

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
}
